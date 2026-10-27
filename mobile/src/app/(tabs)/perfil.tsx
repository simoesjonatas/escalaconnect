import Ionicons from '@expo/vector-icons/Ionicons';
import Constants from 'expo-constants';
import { router } from 'expo-router';
import * as Updates from 'expo-updates';
import { ComponentProps, ReactNode, useState } from 'react';
import { ActivityIndicator, Alert, Linking, Platform, Pressable, Text, View } from 'react-native';

import { verificarAtualizacaoAgora } from '../../lib/atualizacoes';
import { useAuth } from '../../lib/auth';
import { useAgenda } from '../../lib/hooks';
import { useTema } from '../../lib/tema';
import { BUILD_ATUAL } from '../../lib/versao';
import { Cartao, Rotulo, Subtitulo, Suave, Tela } from '../../lib/ui';

type Icone = ComponentProps<typeof Ionicons>['name'];

/** "Maria da Silva" -> "MS" */
const iniciais = (nome: string) =>
  nome
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join('');

/** "21971347985" -> "(21) 97134-7985"; outros formatos ficam como vieram. */
function telefoneFormatado(telefone: string) {
  const d = telefone.replace(/\D/g, '');
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return telefone;
}

function Contato({ icone, texto, vazio }: { icone: Icone; texto: string | null; vazio: string }) {
  const { cores } = useTema();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
      <Ionicons name={icone} size={16} color={cores.textoSuave} />
      <Text numberOfLines={1} style={{ flex: 1, fontSize: 15, color: texto ? cores.texto : cores.pendente }}>
        {texto || vazio}
      </Text>
    </View>
  );
}

/** Grupo de opções com título, numa caixa só (como nos ajustes do celular). */
function Grupo({ titulo, children }: { titulo?: string; children: ReactNode }) {
  return (
    <View style={{ gap: 6 }}>
      {titulo && <Rotulo style={{ marginLeft: 4 }}>{titulo}</Rotulo>}
      {/* A margem negativa esconde a linha divisória do último item. */}
      <Cartao style={{ padding: 0, gap: 0, overflow: 'hidden' }}>
        <View style={{ marginBottom: -1 }}>{children}</View>
      </Cartao>
    </View>
  );
}

function Item({
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
  const cor = perigo ? cores.perigo : cores.texto;
  return (
    <Pressable
      onPress={aoTocar}
      disabled={carregando}
      accessibilityRole="button"
      style={({ pressed }) => [
        {
          flexDirection: 'row',
          alignItems: 'center',
          gap: 12,
          paddingHorizontal: 16,
          paddingVertical: 14,
          borderBottomWidth: 1,
          borderBottomColor: cores.borda,
        },
        pressed && { backgroundColor: cores.fundo },
      ]}>
      <Ionicons name={icone} size={20} color={perigo ? cores.perigo : cores.primaria} />
      <Text style={{ flex: 1, fontSize: 16, color: cor }}>{titulo}</Text>
      {carregando ? (
        <ActivityIndicator size="small" color={cores.textoSuave} />
      ) : (
        !perigo && <Ionicons name="chevron-forward" size={18} color={cores.textoSuave} />
      )}
    </Pressable>
  );
}

export default function Perfil() {
  const { usuario, sair } = useAuth();
  const [verificando, setVerificando] = useState(false);
  const agenda = useAgenda();
  const { cores } = useTema();
  if (!usuario) return null;
  const nome = usuario.nome_completo || usuario.username;

  function assinarAgenda() {
    if (!agenda.data) return;
    // iPhone assina o link (webcal) e a agenda se atualiza sozinha; no Android o .ics é baixado e importado.
    const url = Platform.OS === 'ios' ? agenda.data.webcal : agenda.data.https;
    Linking.openURL(url).catch(() => Alert.alert('Agenda', 'Não foi possível abrir o calendário neste aparelho.'));
  }

  async function verificar() {
    setVerificando(true);
    await verificarAtualizacaoAgora();
    setVerificando(false);
  }

  function confirmarSaida() {
    Alert.alert('Sair', 'Deseja sair da sua conta neste aparelho?', [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Sair', style: 'destructive', onPress: () => void sair() },
    ]);
  }

  return (
    <Tela>
      <Cartao style={{ gap: 14 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <View
            style={{
              width: 56,
              height: 56,
              borderRadius: 28,
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: cores.primaria,
            }}>
            <Text style={{ color: cores.sobrePrimaria, fontSize: 20, fontWeight: '700' }}>{iniciais(nome)}</Text>
          </View>
          <View style={{ flex: 1, gap: 2 }}>
            <Subtitulo>{nome}</Subtitulo>
            <Suave>@{usuario.username}</Suave>
          </View>
        </View>
        <View style={{ gap: 8 }}>
          <Contato icone="mail-outline" texto={usuario.email} vazio="Sem e-mail cadastrado" />
          <Contato
            icone="call-outline"
            texto={usuario.telefone && telefoneFormatado(usuario.telefone)}
            vazio="Sem telefone cadastrado"
          />
        </View>
      </Cartao>

      <Grupo titulo="Meu serviço">
        <Item icone="people-outline" titulo="Minhas equipes" aoTocar={() => router.push('/equipes')} />
        <Item icone="stats-chart-outline" titulo="Meu histórico" aoTocar={() => router.push('/historico')} />
        {agenda.data && (
          <Item icone="calendar-outline" titulo="Minhas escalas no calendário" aoTocar={assinarAgenda} />
        )}
      </Grupo>

      <Grupo titulo="Conta">
        <Item icone="create-outline" titulo="Atualizar contato" aoTocar={() => router.push('/contato')} />
        <Item icone="key-outline" titulo="Trocar senha" aoTocar={() => router.push('/trocar-senha')} />
      </Grupo>

      <Grupo titulo="Aplicativo">
        <Item
          icone="refresh-outline"
          titulo="Verificar atualização"
          aoTocar={verificar}
          carregando={verificando}
        />
      </Grupo>

      <Grupo>
        <Item icone="log-out-outline" titulo="Sair" aoTocar={confirmarSaida} perigo />
      </Grupo>

      <Suave style={{ textAlign: 'center', fontSize: 12 }}>
        Escala Connect {Constants.expoConfig?.version ?? ''} · build {BUILD_ATUAL}
        {Updates.updateId ? ` · atualização ${Updates.updateId.slice(0, 8)}` : ''}
      </Suave>
    </Tela>
  );
}
