import { router } from 'expo-router';
import { useState } from 'react';
import { Alert } from 'react-native';

import { api } from '../lib/api';
import { Botao, Campo, Erro, Suave, Tela } from '../lib/ui';

export default function TrocarSenha() {
  const [atual, setAtual] = useState('');
  const [nova, setNova] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);
  const diferentes = confirmacao.length > 0 && nova !== confirmacao;

  async function enviar() {
    setErro(null);
    setEnviando(true);
    try {
      await api('POST', '/me/trocar-senha/', { senha_atual: atual, nova_senha: nova });
      Alert.alert('Senha alterada', 'Os outros aparelhos conectados à sua conta foram desconectados.');
      router.back();
    } catch (e) {
      setErro(e);
      setEnviando(false);
    }
  }

  return (
    <Tela>
      <Campo rotulo="Senha atual" value={atual} onChangeText={setAtual} senha textContentType="password" />
      <Campo rotulo="Nova senha" value={nova} onChangeText={setNova} senha textContentType="newPassword" />
      <Campo
        rotulo="Repita a nova senha"
        value={confirmacao}
        onChangeText={setConfirmacao}
        senha
        textContentType="newPassword"
      />
      {diferentes && <Suave>As senhas não são iguais.</Suave>}
      <Erro erro={erro} />
      <Botao
        titulo="Trocar senha"
        aoTocar={enviar}
        carregando={enviando}
        desabilitado={!atual || !nova || nova !== confirmacao}
      />
    </Tela>
  );
}
