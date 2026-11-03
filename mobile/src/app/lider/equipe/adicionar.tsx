import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Pressable } from 'react-native';

import { useBuscaDeIntegrantes, useEquipeDoLider, useMudarEquipe } from '../../../lib/hooks';
import { Pessoa } from '../../../lib/types';
import { Avatar, Campo, Cartao, Erro, Estado, Suave, Subtitulo, Tela } from '../../../lib/ui';

/** Busca alguém pelo nome e coloca na equipe já aprovado (como "Adicionar membro" no site). */
export default function AdicionarIntegrante() {
  const equipeId = Number(useLocalSearchParams<{ equipe: string }>().equipe);
  const equipe = useEquipeDoLider(equipeId);
  const mudar = useMudarEquipe();
  const [texto, setTexto] = useState('');
  const [termo, setTermo] = useState('');
  // Espera a pessoa parar de digitar para buscar.
  useEffect(() => {
    const t = setTimeout(() => setTermo(texto.trim()), 350);
    return () => clearTimeout(t);
  }, [texto]);
  const busca = useBuscaDeIntegrantes(equipeId, termo);
  const nomeDaEquipe = equipe.data?.nome ?? 'a equipe';

  function adicionar(pessoa: Pessoa) {
    Alert.alert('Adicionar integrante', `Colocar ${pessoa.nome} na equipe ${nomeDaEquipe}?`, [
      { text: 'Voltar', style: 'cancel' },
      {
        text: 'Adicionar',
        onPress: () =>
          mudar.mutate(
            { tipo: 'adicionar-integrante', equipeId, usuarioId: pessoa.id },
            {
              onSuccess: () => {
                Alert.alert('Pronto', `${pessoa.nome} agora faz parte da equipe ${nomeDaEquipe}.`);
                router.back();
              },
            },
          ),
      },
    ]);
  }

  return (
    <Tela>
      <Campo
        rotulo="Buscar pessoa"
        value={texto}
        onChangeText={setTexto}
        placeholder="Nome ou usuário"
        autoFocus
        autoCorrect={false}
      />
      <Erro erro={mudar.error} />
      {termo.length < 2 ? (
        <Suave style={{ textAlign: 'center' }}>Digite pelo menos 2 letras do nome.</Suave>
      ) : (
        <Estado consulta={busca} vazio={busca.data?.length === 0 && 'Ninguém encontrado fora da equipe com esse nome.'} />
      )}
      {termo.length >= 2 &&
        busca.data?.map((pessoa) => (
          <Pressable
            key={pessoa.id}
            onPress={() => adicionar(pessoa)}
            disabled={mudar.isPending}
            accessibilityRole="button"
            style={({ pressed }) => (pressed || mudar.isPending) && { opacity: 0.6 }}>
            <Cartao style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <Avatar nome={pessoa.nome} />
              <Subtitulo style={{ flex: 1 }}>{pessoa.nome}</Subtitulo>
            </Cartao>
          </Pressable>
        ))}
    </Tela>
  );
}
