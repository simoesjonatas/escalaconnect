import { useState } from 'react';
import { KeyboardAvoidingView, Platform, View } from 'react-native';

import { DadosDoCadastro, useAuth } from '../lib/auth';
import { dataIso, mascaraDeCpf, mascaraDeData } from '../lib/datas';
import { Botao, Campo, Erro, Rotulo, Suave, Tela, Texto } from '../lib/ui';

/**
 * Criar conta pelo app, com as mesmas regras do cadastro do site. Ao terminar a pessoa já entra:
 * aceita o termo do voluntário e, no Início, escolhe as equipes em que quer servir.
 */
export default function Cadastro() {
  const { cadastrar } = useAuth();
  const [nome, setNome] = useState('');
  const [sobrenome, setSobrenome] = useState('');
  const [email, setEmail] = useState('');
  const [cpf, setCpf] = useState('');
  const [telefone, setTelefone] = useState('');
  const [nascimento, setNascimento] = useState('');
  const [senha, setSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);

  const aniversario = dataIso(nascimento);
  const cpfDigitos = cpf.replace(/\D/g, '');
  const completo =
    !!nome.trim() &&
    !!sobrenome.trim() &&
    !!email.trim() &&
    cpfDigitos.length === 11 &&
    !!aniversario &&
    !!senha &&
    !!confirmacao;

  async function enviar() {
    if (!completo || !aniversario) return;
    setErro(null);
    setEnviando(true);
    const dados: DadosDoCadastro = {
      first_name: nome.trim(),
      last_name: sobrenome.trim(),
      email: email.trim(),
      cpf: cpfDigitos,
      telefone: telefone.trim(),
      aniversario,
      password1: senha,
      password2: confirmacao,
    };
    try {
      await cadastrar(dados); // deu certo: o app troca sozinho para a tela do termo
    } catch (e) {
      setErro(e);
      setEnviando(false);
    }
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Tela>
        <Texto>Preencha seus dados para acessar escalas, eventos e disponibilidades da PIBVP.</Texto>

        <Rotulo>Seus dados</Rotulo>
        <View style={{ flexDirection: 'row', gap: 12 }}>
          <View style={{ flex: 1 }}>
            <Campo
              rotulo="Nome"
              value={nome}
              onChangeText={setNome}
              autoCapitalize="words"
              textContentType="givenName"
            />
          </View>
          <View style={{ flex: 1 }}>
            <Campo
              rotulo="Sobrenome"
              value={sobrenome}
              onChangeText={setSobrenome}
              autoCapitalize="words"
              textContentType="familyName"
            />
          </View>
        </View>
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
          rotulo="CPF"
          value={cpf}
          onChangeText={(texto) => setCpf(mascaraDeCpf(texto))}
          keyboardType="number-pad"
          placeholder="000.000.000-00"
          maxLength={14}
        />
        <Campo
          rotulo="Data de nascimento"
          value={nascimento}
          onChangeText={(texto) => setNascimento(mascaraDeData(texto))}
          keyboardType="number-pad"
          placeholder="DD/MM/AAAA"
          maxLength={10}
        />
        <Suave>O CPF e a data de nascimento servem para recuperar a senha se você esquecer.</Suave>
        <Campo
          rotulo="Celular (opcional)"
          value={telefone}
          onChangeText={setTelefone}
          keyboardType="phone-pad"
          textContentType="telephoneNumber"
          placeholder="(21) 99999-9999"
        />

        <Rotulo>Senha</Rotulo>
        <Campo rotulo="Senha" value={senha} onChangeText={setSenha} senha textContentType="newPassword" />
        <Campo
          rotulo="Confirme a senha"
          value={confirmacao}
          onChangeText={setConfirmacao}
          senha
          textContentType="newPassword"
          returnKeyType="go"
          onSubmitEditing={enviar}
        />
        <Suave>Use pelo menos 8 caracteres, sem ser só números e diferente do seu nome.</Suave>

        <Erro erro={erro} />
        <Botao titulo="Criar conta" aoTocar={enviar} carregando={enviando} desabilitado={!completo} />
        <Suave style={{ textAlign: 'center' }}>
          Em seguida você lê e aceita o termo do voluntário e escolhe as equipes em que quer servir.
        </Suave>
      </Tela>
    </KeyboardAvoidingView>
  );
}
