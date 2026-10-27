import Ionicons from '@expo/vector-icons/Ionicons';
import { ComponentProps, ReactNode, useState } from 'react';
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

/**
 * Tela rolável com "puxar para atualizar". O indicador só aparece quando a pessoa puxa:
 * ligá-lo nas atualizações automáticas (ao voltar para o app) deixava o spinner preso
 * no topo do iPhone.
 */
export function Tela({
  children,
  aoAtualizar,
  comTopo,
}: {
  children: ReactNode;
  aoAtualizar?: () => Promise<unknown>;
  /** Respeita a área segura de cima (telas sem cabeçalho do navegador). */
  comTopo?: boolean;
}) {
  const { cores } = useTema();
  const [puxando, setPuxando] = useState(false);

  async function atualizar() {
    setPuxando(true);
    try {
      await aoAtualizar?.();
    } finally {
      setPuxando(false);
    }
  }
  return (
    <SafeAreaView
      style={{ flex: 1, backgroundColor: cores.fundo }}
      edges={comTopo ? ['top', 'left', 'right'] : ['left', 'right']}>
      <ScrollView
        contentContainerStyle={estilos.conteudo}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          aoAtualizar ? (
            <RefreshControl refreshing={puxando} onRefresh={atualizar} tintColor={cores.primaria} />
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
/** Título pequeno em maiúsculas, acima de um grupo (filtros, listas, menu do Perfil). */
export const Rotulo = texto({ fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 }, true);

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

/** Linha rolável de opções em pílula; a selecionada fica destacada. */
export function Opcoes<T extends string>({
  opcoes,
  valor,
  aoEscolher,
}: {
  opcoes: { valor: T; rotulo: string }[];
  valor: T;
  aoEscolher: (valor: T) => void;
}) {
  const { cores } = useTema();
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
      {opcoes.map((opcao) => {
        const ativa = opcao.valor === valor;
        return (
          <Pressable
            key={opcao.valor}
            onPress={() => aoEscolher(opcao.valor)}
            accessibilityRole="button"
            accessibilityState={{ selected: ativa }}
            style={[
              estilos.opcao,
              { borderColor: ativa ? cores.primaria : cores.borda, backgroundColor: ativa ? cores.primaria : cores.cartao },
            ]}>
            <Text style={{ color: ativa ? cores.sobrePrimaria : cores.texto, fontSize: 14, fontWeight: '600' }}>
              {opcao.rotulo}
            </Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

/** Abas internas de largura igual (ex.: Pendências · Cultos · Vagas), com contador opcional. */
/** Número de um selo/contador: acima de 99 vira "99+", para caber no círculo. */
export const contador = (n: number) => (n > 99 ? '99+' : String(n));

export function Segmentos<T extends string>({
  opcoes,
  valor,
  aoEscolher,
}: {
  opcoes: { valor: T; rotulo: string; total?: number }[];
  valor: T;
  aoEscolher: (valor: T) => void;
}) {
  const { cores } = useTema();
  return (
    <View style={[estilos.segmentos, { backgroundColor: cores.borda }]} accessibilityRole="tablist">
      {opcoes.map((opcao) => {
        const ativa = opcao.valor === valor;
        return (
          <Pressable
            key={opcao.valor}
            onPress={() => aoEscolher(opcao.valor)}
            accessibilityRole="tab"
            accessibilityState={{ selected: ativa }}
            style={[estilos.segmento, ativa && { backgroundColor: cores.cartao }]}>
            <Text numberOfLines={1} style={{ color: ativa ? cores.texto : cores.textoSuave, fontSize: 14, fontWeight: '600' }}>
              {opcao.rotulo}
            </Text>
            {!!opcao.total && (
              <View style={[estilos.contador, { backgroundColor: cores.perigo }]}>
                <Text style={estilos.contadorTexto}>{contador(opcao.total)}</Text>
              </View>
            )}
          </Pressable>
        );
      })}
    </View>
  );
}

/** Linha compacta de lista, tocável, com seta à direita (alternativa leve ao Cartao). */
export function Linha({
  titulo,
  detalhe,
  status,
  corStatus,
  aoTocar,
}: {
  titulo: string;
  detalhe?: string;
  status?: string;
  corStatus?: string;
  aoTocar?: () => void;
}) {
  const { cores } = useTema();
  return (
    <Pressable
      onPress={aoTocar}
      disabled={!aoTocar}
      accessibilityRole={aoTocar ? 'button' : undefined}
      style={({ pressed }) => [
        estilos.linha,
        { backgroundColor: cores.cartao, borderColor: cores.borda },
        pressed && { opacity: 0.6 },
      ]}>
      <View style={{ flex: 1, gap: 2 }}>
        <Text numberOfLines={1} style={{ color: cores.texto, fontSize: 15, fontWeight: '600' }}>
          {titulo}
        </Text>
        {!!detalhe && (
          <Text numberOfLines={1} style={{ color: cores.textoSuave, fontSize: 13 }}>
            {detalhe}
          </Text>
        )}
        {!!status && (
          <Text numberOfLines={1} style={{ color: corStatus ?? cores.textoSuave, fontSize: 13, fontWeight: '600' }}>
            {status}
          </Text>
        )}
      </View>
      {aoTocar && <Ionicons name="chevron-forward" size={18} color={cores.textoSuave} />}
    </Pressable>
  );
}

/** "Maria da Silva" -> "MS" */
export const iniciais = (nome: string) =>
  nome
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join('');

/** Círculo com as iniciais da pessoa; `destaque` usa o verde da marca (Perfil). */
export function Avatar({ nome, tamanho = 32, destaque }: { nome: string; tamanho?: number; destaque?: boolean }) {
  const { cores } = useTema();
  return (
    <View
      style={{
        width: tamanho,
        height: tamanho,
        borderRadius: tamanho / 2,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: destaque ? cores.primaria : cores.fundo,
        borderWidth: destaque ? 0 : 1,
        borderColor: cores.borda,
      }}>
      <Text
        style={{
          color: destaque ? cores.sobrePrimaria : cores.textoSuave,
          fontSize: Math.round(tamanho * 0.37),
          fontWeight: '700',
        }}>
        {iniciais(nome)}
      </Text>
    </View>
  );
}

export type Icone = ComponentProps<typeof Ionicons>['name'];

/** Grupo de opções numa caixa só, com título opcional (como nos ajustes do celular). */
export function Grupo({ titulo, children }: { titulo?: string; children: ReactNode }) {
  return (
    <View style={{ gap: 6 }}>
      {titulo && <Rotulo style={{ marginLeft: 4 }}>{titulo}</Rotulo>}
      <Cartao style={{ padding: 0, gap: 0, overflow: 'hidden' }}>
        {/* A margem negativa esconde a linha divisória do último item. */}
        <View style={{ marginBottom: -1 }}>{children}</View>
      </Cartao>
    </View>
  );
}

/** Uma linha de um Grupo: ícone, título e seta (ou rodinha enquanto `carregando`). */
export function ItemDeGrupo({
  icone,
  titulo,
  aoTocar,
  perigo,
  carregando,
}: {
  icone: Icone;
  titulo: string;
  aoTocar: () => void;
  perigo?: boolean;
  carregando?: boolean;
}) {
  const { cores } = useTema();
  return (
    <Pressable
      onPress={aoTocar}
      disabled={carregando}
      accessibilityRole="button"
      style={({ pressed }) => [
        estilos.itemDeGrupo,
        { borderBottomColor: cores.borda },
        pressed && { backgroundColor: cores.fundo },
      ]}>
      <Ionicons name={icone} size={20} color={perigo ? cores.perigo : cores.primaria} />
      <Text style={{ flex: 1, fontSize: 16, color: perigo ? cores.perigo : cores.texto }}>{titulo}</Text>
      {carregando ? (
        <ActivityIndicator size="small" color={cores.textoSuave} />
      ) : (
        !perigo && <Ionicons name="chevron-forward" size={18} color={cores.textoSuave} />
      )}
    </Pressable>
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
  opcao: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 7 },
  segmentos: { flexDirection: 'row', borderRadius: 10, padding: 3, gap: 3 },
  segmento: {
    flex: 1,
    minHeight: 38,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingHorizontal: 4,
  },
  contador: { minWidth: 20, height: 20, borderRadius: 10, paddingHorizontal: 5, alignItems: 'center', justifyContent: 'center' },
  contadorTexto: { color: '#fff', fontSize: 12, fontWeight: '700' },
  linha: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: espaco.m,
    paddingVertical: 10,
  },
  itemDeGrupo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: espaco.g,
    paddingVertical: 14,
    borderBottomWidth: 1,
  },
  etiqueta: { alignSelf: 'flex-start', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3 },
  etiquetaTexto: { color: '#fff', fontSize: 12, fontWeight: '700' },
});
