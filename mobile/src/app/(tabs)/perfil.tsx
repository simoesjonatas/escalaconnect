import Ionicons from '@expo/vector-icons/Ionicons';
import Constants from 'expo-constants';
import { router } from 'expo-router';
import * as Updates from 'expo-updates';
import { useState } from 'react';
import { Alert, Linking, Platform, Text, View } from 'react-native';

import { verificarAtualizacaoAgora } from '../../lib/atualizacoes';
import { useAuth } from '../../lib/auth';
import { useAgenda } from '../../lib/hooks';
import { useTema } from '../../lib/tema';
import { BUILD_ATUAL } from '../../lib/versao';
import { Avatar, Cartao, Grupo, Icone, ItemDeGrupo, Subtitulo, Suave, Tela } from '../../lib/ui';

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

export default function Perfil() {
  const { usuario, sair } = useAuth();
  const [verificando, setVerificando] = useState(false);
  const agenda = useAgenda();
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
          <Avatar nome={nome} tamanho={56} destaque />
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
        <ItemDeGrupo icone="people-outline" titulo="Minhas equipes" aoTocar={() => router.push('/equipes')} />
        <ItemDeGrupo icone="stats-chart-outline" titulo="Meu histórico" aoTocar={() => router.push('/historico')} />
        {agenda.data && (
          <ItemDeGrupo icone="calendar-outline" titulo="Minhas escalas no calendário" aoTocar={assinarAgenda} />
        )}
      </Grupo>

      <Grupo titulo="Conta">
        <ItemDeGrupo icone="create-outline" titulo="Atualizar contato" aoTocar={() => router.push('/contato')} />
        <ItemDeGrupo icone="key-outline" titulo="Trocar senha" aoTocar={() => router.push('/trocar-senha')} />
      </Grupo>

      <Grupo titulo="Aplicativo">
        <ItemDeGrupo
          icone="refresh-outline"
          titulo="Verificar atualização"
          aoTocar={verificar}
          carregando={verificando}
        />
      </Grupo>

      <Grupo>
        <ItemDeGrupo icone="log-out-outline" titulo="Sair" aoTocar={confirmarSaida} perigo />
      </Grupo>

      <Suave style={{ textAlign: 'center', fontSize: 12 }}>
        Escala Connect {Constants.expoConfig?.version ?? ''} · build {BUILD_ATUAL}
        {Updates.updateId ? ` · atualização ${Updates.updateId.slice(0, 8)}` : ''}
      </Suave>
    </Tela>
  );
}
