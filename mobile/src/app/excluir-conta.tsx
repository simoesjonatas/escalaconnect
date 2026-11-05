import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, Text, View } from 'react-native';

import { useAuth } from '../lib/auth';
import { useTema } from '../lib/tema';
import { Botao, Campo, Cartao, Erro, Subtitulo, Suave, Tela, Texto } from '../lib/ui';

const O_QUE_ACONTECE = [
  'Seu nome, e-mail, CPF, telefone e datas são apagados e você não consegue mais entrar.',
  'Você sai de todas as equipes e suas disponibilidades são apagadas.',
  'Suas próximas escalas ficam em aberto e a liderança é avisada.',
  'As escalas em que você já serviu continuam no histórico, como "Ex-voluntário".',
];

/** Exigência da Apple e do Google: excluir a conta pelo próprio app (mesma regra do site). */
export default function ExcluirConta() {
  const { excluirConta, usuario } = useAuth();
  const { cores } = useTema();
  const [senha, setSenha] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);

  function confirmar() {
    Alert.alert('Excluir conta', 'Tem certeza? Não dá para desfazer.', [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Excluir', style: 'destructive', onPress: () => void excluir() },
    ]);
  }

  async function excluir() {
    setErro(null);
    setEnviando(true);
    try {
      await excluirConta(senha); // deu certo: a sessão é limpa e o app volta ao login
      Alert.alert('Conta excluída', 'Obrigado por ter servido conosco!');
    } catch (e) {
      setErro(e);
      setEnviando(false);
    }
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Tela>
        <Cartao style={{ borderColor: cores.perigo }}>
          <Subtitulo>Ao excluir sua conta</Subtitulo>
          {O_QUE_ACONTECE.map((item) => (
            <View key={item} style={{ flexDirection: 'row', gap: 8 }}>
              <Ionicons name="ellipse" size={6} color={cores.textoSuave} style={{ marginTop: 8 }} />
              <Text style={{ flex: 1, fontSize: 15, lineHeight: 21, color: cores.texto }}>{item}</Text>
            </View>
          ))}
          <Texto style={{ color: cores.perigo, fontWeight: '600' }}>
            Não dá para desfazer. Para voltar depois, será preciso criar uma conta nova.
          </Texto>
        </Cartao>
        {usuario?.lider && <Suave>Você também deixa de ser líder das suas equipes.</Suave>}

        <Campo
          rotulo="Digite sua senha para confirmar"
          value={senha}
          onChangeText={setSenha}
          senha
          textContentType="password"
          returnKeyType="go"
          onSubmitEditing={() => senha && confirmar()}
        />
        <Erro erro={erro} />
        <Botao
          titulo="Excluir minha conta"
          variante="perigo"
          aoTocar={confirmar}
          carregando={enviando}
          desabilitado={!senha}
        />
      </Tela>
    </KeyboardAvoidingView>
  );
}
