import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform } from 'react-native';

import { api } from '../lib/api';
import { Botao, Campo, Cartao, Erro, Suave, Subtitulo, Tela, Texto } from '../lib/ui';

/** "07011996" -> "07/01/1996", conforme a pessoa digita. */
function mascaraDeData(texto: string) {
  const digitos = texto.replace(/\D/g, '').slice(0, 8);
  return [digitos.slice(0, 2), digitos.slice(2, 4), digitos.slice(4)].filter(Boolean).join('/');
}

/** "07/01/1996" -> "1996-01-07"; null enquanto incompleta. */
function dataIso(texto: string) {
  const partes = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(texto);
  return partes ? `${partes[3]}-${partes[2]}-${partes[1]}` : null;
}

/** Mesmo fluxo do site: CPF + data de nascimento, e o link para criar a senha nova chega por e-mail. */
export default function EsqueciSenha() {
  const [cpf, setCpf] = useState('');
  const [nascimento, setNascimento] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);
  const [enviadoPara, setEnviadoPara] = useState<string | null>(null);
  const data = dataIso(nascimento);

  async function enviar() {
    if (!data) return;
    setErro(null);
    setEnviando(true);
    try {
      const { email } = await api<{ email: string }>('POST', '/auth/recuperar-senha/', { cpf, data_nascimento: data });
      setEnviadoPara(email);
    } catch (e) {
      setErro(e);
    }
    setEnviando(false);
  }

  if (enviadoPara) {
    return (
      <Tela>
        <Cartao>
          <Subtitulo>Confira seu e-mail</Subtitulo>
          <Texto>Enviamos um link para {enviadoPara}. Abra o e-mail, toque no link e crie sua senha nova.</Texto>
          <Suave>O link vale por 15 minutos. Se não achar o e-mail, olhe também no spam.</Suave>
        </Cartao>
        <Suave>Depois de criar a senha, volte aqui e entre com ela.</Suave>
        <Botao titulo="Voltar para o login" aoTocar={() => router.back()} />
      </Tela>
    );
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Tela>
        <Texto>Informe seu CPF e sua data de nascimento. Vamos mandar um link para o e-mail da sua conta.</Texto>
        <Campo
          rotulo="CPF"
          value={cpf}
          onChangeText={setCpf}
          keyboardType="number-pad"
          placeholder="Só os números"
          maxLength={14}
        />
        <Campo
          rotulo="Data de nascimento"
          value={nascimento}
          onChangeText={(texto) => setNascimento(mascaraDeData(texto))}
          keyboardType="number-pad"
          placeholder="DD/MM/AAAA"
          maxLength={10}
          returnKeyType="go"
          onSubmitEditing={enviar}
        />
        <Erro erro={erro} />
        <Botao
          titulo="Enviar link"
          aoTocar={enviar}
          carregando={enviando}
          desabilitado={cpf.replace(/\D/g, '').length !== 11 || !data}
        />
      </Tela>
    </KeyboardAvoidingView>
  );
}
