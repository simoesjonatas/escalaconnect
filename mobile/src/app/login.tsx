import { useState } from 'react';
import { Image, KeyboardAvoidingView, Platform, View } from 'react-native';

import { useAuth } from '../lib/auth';
import { Botao, Campo, Erro, Suave, Tela, Titulo } from '../lib/ui';

export default function Login() {
  const { entrar } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);

  async function enviar() {
    setErro(null);
    setEnviando(true);
    try {
      await entrar(username.trim(), password);
    } catch (e) {
      setErro(e);
      setEnviando(false);
    }
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Tela comTopo>
        <View style={{ alignItems: 'center', gap: 8, marginVertical: 32 }}>
          <Image source={require('../../assets/icon.png')} style={{ width: 96, height: 96, borderRadius: 20 }} />
          <Titulo>Escala Connect</Titulo>
          <Suave>Entre com o mesmo usuário do site.</Suave>
        </View>
        <Campo
          rotulo="Usuário ou e-mail"
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          textContentType="username"
          returnKeyType="next"
        />
        <Campo
          rotulo="Senha"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          textContentType="password"
          returnKeyType="go"
          onSubmitEditing={enviar}
        />
        <Erro erro={erro} />
        <Botao titulo="Entrar" aoTocar={enviar} carregando={enviando} desabilitado={!username.trim() || !password} />
      </Tela>
    </KeyboardAvoidingView>
  );
}
