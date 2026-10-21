import Constants from 'expo-constants';
import { router } from 'expo-router';
import * as Updates from 'expo-updates';
import { useState } from 'react';
import { Alert } from 'react-native';

import { verificarAtualizacaoAgora } from '../../lib/atualizacoes';
import { useAuth } from '../../lib/auth';
import { BUILD_ATUAL } from '../../lib/versao';
import { Botao, Cartao, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

export default function Perfil() {
  const { usuario, sair } = useAuth();
  const [verificando, setVerificando] = useState(false);
  if (!usuario) return null;

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
      <Cartao>
        <Subtitulo>{usuario.nome_completo || usuario.username}</Subtitulo>
        <Suave>Usuário: {usuario.username}</Suave>
        <Texto>{usuario.email || 'Sem e-mail cadastrado'}</Texto>
        <Texto>{usuario.telefone || 'Sem telefone cadastrado'}</Texto>
      </Cartao>
      <Botao titulo="Atualizar contato" variante="secundario" aoTocar={() => router.push('/contato')} />
      <Botao titulo="Minhas equipes" variante="secundario" aoTocar={() => router.push('/equipes')} />
      <Botao titulo="Trocar senha" variante="secundario" aoTocar={() => router.push('/trocar-senha')} />
      <Botao titulo="Verificar atualização" variante="secundario" carregando={verificando} aoTocar={verificar} />
      <Botao titulo="Sair" variante="perigo" aoTocar={confirmarSaida} />
      <Suave style={{ textAlign: 'center' }}>
        Escala Connect {Constants.expoConfig?.version ?? ''} · build {BUILD_ATUAL}
        {Updates.updateId ? ` · atualização ${Updates.updateId.slice(0, 8)}` : ''}
      </Suave>
    </Tela>
  );
}
