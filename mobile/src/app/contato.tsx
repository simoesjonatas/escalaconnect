import { useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';

import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { Usuario } from '../lib/types';
import { Botao, Campo, Erro, Tela } from '../lib/ui';

export default function Contato() {
  const { usuario, atualizarUsuario } = useAuth();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState(usuario?.email ?? '');
  const [telefone, setTelefone] = useState(usuario?.telefone ?? '');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);

  async function salvar() {
    setErro(null);
    setEnviando(true);
    try {
      await atualizarUsuario(await api<Usuario>('PATCH', '/me/', { email: email.trim(), telefone: telefone.trim() }));
      void queryClient.invalidateQueries({ queryKey: ['home'] }); // some o aviso de contato incompleto
      router.back();
    } catch (e) {
      setErro(e);
      setEnviando(false);
    }
  }

  return (
    <Tela>
      <Campo
        rotulo="E-mail"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="email-address"
        textContentType="emailAddress"
      />
      <Campo
        rotulo="Telefone com DDD"
        value={telefone}
        onChangeText={setTelefone}
        keyboardType="phone-pad"
        textContentType="telephoneNumber"
        placeholder="(21) 99999-9999"
      />
      <Erro erro={erro} />
      <Botao titulo="Salvar" aoTocar={salvar} carregando={enviando} desabilitado={!email.trim()} />
    </Tela>
  );
}
