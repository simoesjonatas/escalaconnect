import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { AuthProvider, EstadoDaSessao, useAuth } from '../lib/auth';
import { usePush } from '../lib/push';
import { useTema } from '../lib/tema';
import { TelaDeAtualizacao, useAtualizacaoObrigatoria } from '../lib/versao';

export default function RootLayout() {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } }),
  );
  const { cores, escuro } = useTema();
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
          <Navegacao />
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

function Telas({ estado }: { estado: EstadoDaSessao }) {
  const { cores } = useTema();
  return (
    <Stack
      screenOptions={{
        headerTintColor: cores.primaria,
        headerTitleStyle: { color: cores.texto },
        headerStyle: { backgroundColor: cores.cartao },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: cores.fundo },
      }}>
      <Stack.Protected guard={estado === 'anonimo'}>
        <Stack.Screen name="login" options={{ headerShown: false }} />
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
        <Stack.Screen name="contato" options={{ title: 'Meu contato' }} />
        <Stack.Screen name="trocar-senha" options={{ title: 'Trocar senha' }} />
      </Stack.Protected>
    </Stack>
  );
}
