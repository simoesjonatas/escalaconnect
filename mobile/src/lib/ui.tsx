import { ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
  ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { mensagemDeErro } from './api';
import { cores, espaco } from './tema';

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
  return (
    <SafeAreaView style={estilos.tela} edges={comTopo ? ['top', 'left', 'right'] : ['left', 'right']}>
      <ScrollView
        contentContainerStyle={estilos.conteudo}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          aoAtualizar ? <RefreshControl refreshing={!!atualizando} onRefresh={aoAtualizar} /> : undefined
        }>
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function Cartao({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <View style={[estilos.cartao, style]}>{children}</View>;
}

export const Titulo = ({ children }: { children: ReactNode }) => <Text style={estilos.titulo}>{children}</Text>;
export const Subtitulo = ({ children }: { children: ReactNode }) => <Text style={estilos.subtitulo}>{children}</Text>;
export const Texto = ({ children }: { children: ReactNode }) => <Text style={estilos.texto}>{children}</Text>;
export const Suave = ({ children }: { children: ReactNode }) => <Text style={estilos.suave}>{children}</Text>;

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

export function Campo({ rotulo, ...props }: { rotulo: string } & TextInputProps) {
  return (
    <View style={{ gap: 4 }}>
      <Text style={estilos.rotulo}>{rotulo}</Text>
      <TextInput placeholderTextColor={cores.textoSuave} {...props} style={[estilos.campo, props.style]} />
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
  if (!erro) return null;
  return <Text style={estilos.erro}>{mensagemDeErro(erro)}</Text>;
}

/** Estados de uma consulta: carregando, erro (com "tentar de novo") ou vazio. Devolve null se há o que mostrar. */
export function Estado({
  consulta,
  vazio,
}: {
  consulta: { isPending: boolean; error: unknown; refetch: () => unknown };
  vazio?: string | false;
}) {
  if (consulta.isPending) return <ActivityIndicator style={{ marginTop: espaco.gg }} color={cores.primaria} />;
  if (consulta.error) {
    return (
      <Cartao>
        <Erro erro={consulta.error} />
        <Botao titulo="Tentar de novo" variante="secundario" aoTocar={() => consulta.refetch()} />
      </Cartao>
    );
  }
  if (vazio) return <Text style={[estilos.suave, { textAlign: 'center', marginTop: espaco.gg }]}>{vazio}</Text>;
  return null;
}

const estilos = StyleSheet.create({
  tela: { flex: 1, backgroundColor: cores.fundo },
  conteudo: { padding: espaco.g, gap: espaco.m },
  cartao: {
    backgroundColor: cores.cartao,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espaco.g,
    gap: espaco.p,
  },
  titulo: { fontSize: 24, fontWeight: '700', color: cores.texto },
  subtitulo: { fontSize: 17, fontWeight: '600', color: cores.texto },
  texto: { fontSize: 15, color: cores.texto, lineHeight: 21 },
  suave: { fontSize: 14, color: cores.textoSuave, lineHeight: 20 },
  botao: {
    minHeight: 48,
    borderRadius: 10,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: espaco.g,
  },
  botaoTexto: { fontSize: 16, fontWeight: '600' },
  rotulo: { fontSize: 14, fontWeight: '600', color: cores.texto },
  campo: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: 10,
    paddingHorizontal: espaco.m,
    fontSize: 16,
    color: cores.texto,
    backgroundColor: cores.cartao,
  },
  etiqueta: { alignSelf: 'flex-start', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3 },
  etiquetaTexto: { color: '#fff', fontSize: 12, fontWeight: '700' },
  erro: { color: cores.perigo, fontSize: 14 },
});
