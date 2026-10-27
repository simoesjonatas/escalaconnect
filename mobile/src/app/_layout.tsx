import Ionicons from '@expo/vector-icons/Ionicons';
import { focusManager, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DarkTheme, DefaultTheme, router, Stack, ThemeProvider } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { ActivityIndicator, AppState, Pressable, Text, View } from 'react-native';

import { FaixaDeAtualizacao, useVerificarAtualizacoes } from '../lib/atualizacoes';
import { AuthProvider, EstadoDaSessao, useAuth } from '../lib/auth';
import { usePush } from '../lib/push';
import { useTema } from '../lib/tema';
import { TelaDeAtualizacao, useAtualizacaoObrigatoria } from '../lib/versao';

// Ao voltar para o app, o React Query atualiza o que estiver desatualizado (sino, contadores, listas).
focusManager.setEventListener((aoMudarFoco) => {
  const inscricao = AppState.addEventListener('change', (estado) => aoMudarFoco(estado === 'active'));
  return () => inscricao.remove();
});

export default function RootLayout() {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } }),
  );
  const { cores, escuro } = useTema();
  useVerificarAtualizacoes();
  // Cores do navegador (cabeçalhos, fundo das transições) acompanham o tema do aparelho.
  const base = escuro ? DarkTheme : DefaultTheme;
  const tema = {
    ...base,
    colors: { ...base.colors, primary: cores.primaria, background: cores.fundo, card: cores.cartao, text: cores.texto, border: cores.borda },
  };
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider value={tema}>
          <StatusBar style={escuro ? 'light' : 'dark'} />
          {/* Container para a faixa de atualização ficar sobreposta às telas. */}
          <View style={{ flex: 1 }}>
            <Navegacao />
            <FaixaDeAtualizacao />
          </View>
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

/** Cada grupo de telas só existe no estado de sessão correspondente (ver lib/auth.tsx). */
function Navegacao() {
  const { estado } = useAuth();
  const { cores } = useTema();
  const atualizacao = useAtualizacaoObrigatoria();
  if (atualizacao) return <TelaDeAtualizacao meta={atualizacao} />;
  if (estado === 'carregando') {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: cores.fundo }}>
        <ActivityIndicator size="large" color={cores.primaria} />
      </View>
    );
  }
  return (
    <>
      {estado === 'liberado' && <Push />}
      <Telas estado={estado} />
    </>
  );
}

function Push() {
  usePush();
  return null;
}

function VoltarAoInicio() {
  const { cores } = useTema();
  return (
    <Pressable
      onPress={() => router.replace('/')}
      accessibilityRole="button"
      accessibilityLabel="Voltar ao início"
      hitSlop={8}
      style={({ pressed }) => [
        { flexDirection: 'row', alignItems: 'center', gap: 2, paddingHorizontal: 6 },
        pressed && { opacity: 0.6 },
      ]}>
      <Ionicons name="chevron-back" size={24} color={cores.texto} />
      <Text style={{ color: cores.texto, fontSize: 17 }}>Voltar</Text>
    </Pressable>
  );
}

function Telas({ estado }: { estado: EstadoDaSessao }) {
  const { cores } = useTema();
  return (
    <Stack
      screenOptions={({ navigation }) => ({
        headerTintColor: cores.primaria,
        headerTitleStyle: { color: cores.texto },
        headerStyle: { backgroundColor: cores.cartao },
        headerShadowVisible: false,
        // Sem isto o iPhone mostra o nome da rota anterior ("(tabs)") no botão de voltar.
        headerBackTitle: 'Voltar',
        contentStyle: { backgroundColor: cores.fundo },
        // Tela aberta direto por um link, sem nada antes: o Voltar leva ao Início.
        ...(!navigation.canGoBack() && { headerLeft: () => <VoltarAoInicio /> }),
      })}>
      <Stack.Protected guard={estado === 'anonimo'}>
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="esqueci-senha" options={{ title: 'Esqueci minha senha' }} />
      </Stack.Protected>
      <Stack.Protected guard={estado === 'senha'}>
        <Stack.Screen name="definir-senha" options={{ headerShown: false }} />
      </Stack.Protected>
      <Stack.Protected guard={estado === 'termo'}>
        <Stack.Screen name="termo" options={{ headerShown: false }} />
      </Stack.Protected>
      <Stack.Protected guard={estado === 'liberado'}>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="escala/[id]" options={{ title: 'Escala' }} />
        <Stack.Screen name="periodo/por-evento" options={{ title: 'Registrar disponibilidade' }} />
        <Stack.Screen name="equipes" options={{ title: 'Minhas equipes' }} />
        <Stack.Screen name="historico" options={{ title: 'Meu histórico' }} />
        <Stack.Screen name="contato" options={{ title: 'Meu contato' }} />
        <Stack.Screen name="trocar-senha" options={{ title: 'Trocar senha' }} />
        <Stack.Screen name="lider/vaga/[id]" options={{ title: 'Escalar na vaga' }} />
        <Stack.Screen name="lider/culto/[id]" options={{ title: 'Culto' }} />
        <Stack.Screen name="lider/disponibilidade" options={{ title: 'Pedir disponibilidade' }} />
        <Stack.Screen name="vagas" options={{ title: 'Vagas em aberto' }} />
        <Stack.Screen name="avisos" options={{ title: 'Avisos' }} />
      </Stack.Protected>
    </Stack>
  );
}
