import Ionicons from '@expo/vector-icons/Ionicons';
import { ReactNode, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  TextStyle,
  View,
  ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { mensagemDeErro } from './api';
import { espaco, useTema } from './tema';

/** Tela rolável com "puxar para atualizar". */
export function Tela({
  children,
  atualizando,
  aoAtualizar,
  comTopo,
}: {
  children: ReactNode;
  atualizando?: boolean;
  aoAtualizar?: () => void;
  /** Respeita a área segura de cima (telas sem cabeçalho do navegador). */
  comTopo?: boolean;
}) {
  const { cores } = useTema();
  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: cores.fundo }}
      edges={comTopo ? ['top', 'left', 'right'] : ['left', 'right']}>
      <ScrollView
        contentContainerStyle={estilos.conteudo}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          aoAtualizar ? (
            <RefreshControl refreshing={!!atualizando} onRefresh={aoAtualizar} tintColor={cores.primaria} />
          ) : undefined
        }>
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function Cartao({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  const { cores } = useTema();
  return (
    <View style={[estilos.cartao, { backgroundColor: cores.cartao, borderColor: cores.borda }, style]}>{children}</View>
  );
}

function texto(estilo: TextStyle, suave = false) {
  return function Texto({ children, style }: { children: ReactNode; style?: TextStyle }) {
    const { cores } = useTema();
    return <Text style={[estilo, { color: suave ? cores.textoSuave : cores.texto }, style]}>{children}</Text>;
  };
}

export const Titulo = texto({ fontSize: 24, fontWeight: '700' });
export const Subtitulo = texto({ fontSize: 17, fontWeight: '600' });
export const Texto = texto({ fontSize: 15, lineHeight: 21 });
export const Suave = texto({ fontSize: 14, lineHeight: 20 }, true);

/** Logo da marca (o mesmo arquivo do ícone do app). */
export function Logo({ tamanho = 96 }: { tamanho?: number }) {
  return (
    <Image
      source={require('../../assets/icon.png')}
      style={{ width: tamanho, height: tamanho, borderRadius: tamanho / 5 }}
      accessibilityLabel="Connect"
    />
  );
}

export function Botao({
  titulo,
  aoTocar,
  variante = 'primario',
  carregando,
  desabilitado,
}: {
  titulo: string;
  aoTocar: () => void;
  variante?: 'primario' | 'secundario' | 'perigo';
  carregando?: boolean;
  desabilitado?: boolean;
}) {
  const { cores } = useTema();
  const cheio = variante === 'primario';
  const cor = variante === 'perigo' ? cores.perigo : cores.primaria;
  return (
    <Pressable
      accessibilityRole="button"
      disabled={carregando || desabilitado}
      onPress={aoTocar}
      style={({ pressed }) => [
        estilos.botao,
        { borderColor: cor, backgroundColor: cheio ? cor : 'transparent' },
        (pressed || carregando || desabilitado) && { opacity: 0.6 },
      ]}>
      {carregando ? (
        <ActivityIndicator color={cheio ? cores.sobrePrimaria : cor} />
      ) : (
        <Text style={[estilos.botaoTexto, { color: cheio ? cores.sobrePrimaria : cor }]}>{titulo}</Text>
      )}
    </Pressable>
  );
}

export function Campo({ rotulo, senha, ...props }: { rotulo: string; senha?: boolean } & TextInputProps) {
  const { cores } = useTema();
  const [mostrar, setMostrar] = useState(false);
  return (
    <View style={{ gap: 4 }}>
      <Text style={[estilos.rotulo, { color: cores.texto }]}>{rotulo}</Text>
      <View>
        <TextInput
          placeholderTextColor={cores.textoSuave}
          secureTextEntry={senha && !mostrar}
          {...props}
          style={[
            estilos.campo,
            { borderColor: cores.borda, backgroundColor: cores.cartao, color: cores.texto },
            senha && { paddingRight: 48 },
            props.style,
          ]}
        />
        {senha && (
          <Pressable
            onPress={() => setMostrar((m) => !m)}
            hitSlop={8}
            accessibilityRole="button"
            accessibilityLabel={mostrar ? 'Ocultar senha' : 'Mostrar senha'}
            style={estilos.olho}>
            <Ionicons name={mostrar ? 'eye-off-outline' : 'eye-outline'} size={22} color={cores.textoSuave} />
          </Pressable>
        )}
      </View>
    </View>
  );
}

export function Etiqueta({ texto, cor }: { texto: string; cor: string }) {
  return (
    <View style={[estilos.etiqueta, { backgroundColor: cor }]}>
      <Text style={estilos.etiquetaTexto}>{texto}</Text>
    </View>
  );
}

export function Erro({ erro }: { erro: unknown }) {
  const { cores } = useTema();
  if (!erro) return null;
  return <Text style={{ color: cores.perigo, fontSize: 14 }}>{mensagemDeErro(erro)}</Text>;
}

/** Estados de uma consulta: carregando, erro (com "tentar de novo") ou vazio. Devolve null se há o que mostrar. */
export function Estado({
  consulta,
  vazio,
}: {
  consulta: { isPending: boolean; error: unknown; refetch: () => unknown };
  vazio?: string | false;
}) {
  const { cores } = useTema();
  if (consulta.isPending) return <ActivityIndicator style={{ marginTop: espaco.gg }} color={cores.primaria} />;
  if (consulta.error) {
    return (
      <Cartao>
        <Erro erro={consulta.error} />
        <Botao titulo="Tentar de novo" variante="secundario" aoTocar={() => consulta.refetch()} />
      </Cartao>
    );
  }
  if (vazio) return <Suave style={{ textAlign: 'center', marginTop: espaco.gg }}>{vazio}</Suave>;
  return null;
}

const estilos = StyleSheet.create({
  conteudo: { padding: espaco.g, gap: espaco.m },
  cartao: { borderRadius: 12, borderWidth: 1, padding: espaco.g, gap: espaco.p },
  botao: {
    minHeight: 48,
    borderRadius: 10,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: espaco.g,
  },
  botaoTexto: { fontSize: 16, fontWeight: '600' },
  rotulo: { fontSize: 14, fontWeight: '600' },
  campo: { minHeight: 48, borderWidth: 1, borderRadius: 10, paddingHorizontal: espaco.m, fontSize: 16 },
  olho: { position: 'absolute', right: 12, top: 0, bottom: 0, justifyContent: 'center' },
  etiqueta: { alignSelf: 'flex-start', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3 },
  etiquetaTexto: { color: '#fff', fontSize: 12, fontWeight: '700' },
});
