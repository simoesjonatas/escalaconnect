import { router } from 'expo-router';
import { Alert } from 'react-native';

import { useAuth } from '../../lib/auth';
import { Botao, Cartao, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

export default function Perfil() {
  const { usuario, sair } = useAuth();
  if (!usuario) return null;

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
      <Botao titulo="Sair" variante="perigo" aoTocar={confirmarSaida} />
    </Tela>
  );
}
