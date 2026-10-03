import { useState } from 'react';

import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Usuario } from '../lib/types';
import { Botao, Campo, Erro, Suave, Tela, Titulo } from '../lib/ui';

/** Primeiro acesso de uma conta criada pelo líder: troca a senha provisória. */
export default function DefinirSenha() {
  const { atualizarUsuario, sair } = useAuth();
  const [senha, setSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);
  const diferentes = confirmacao.length > 0 && senha !== confirmacao;

  async function enviar() {
    setErro(null);
    setEnviando(true);
    try {
      await atualizarUsuario(await api<Usuario>('POST', '/me/definir-senha/', { nova_senha: senha }));
    } catch (e) {
      setErro(e);
      setEnviando(false);
    }
  }

  return (
    <Tela comTopo>
      <Titulo>Crie sua senha</Titulo>
      <Suave>Este é seu primeiro acesso. Escolha uma senha nova para continuar.</Suave>
      <Campo rotulo="Nova senha" value={senha} onChangeText={setSenha} senha textContentType="newPassword" />
      <Campo
        rotulo="Repita a nova senha"
        value={confirmacao}
        onChangeText={setConfirmacao}
        senha
        textContentType="newPassword"
      />
      {diferentes && <Suave>As senhas não são iguais.</Suave>}
      <Erro erro={erro} />
      <Botao titulo="Salvar senha" aoTocar={enviar} carregando={enviando} desabilitado={!senha || senha !== confirmacao} />
      <Botao titulo="Sair" variante="secundario" aoTocar={sair} />
    </Tela>
  );
}
