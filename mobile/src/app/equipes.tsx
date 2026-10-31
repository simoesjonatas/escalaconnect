import Ionicons from '@expo/vector-icons/Ionicons';
import { ReactNode } from 'react';
import { ActivityIndicator, Alert, Pressable, Text, View } from 'react-native';

import { useCandidatura, useEquipes } from '../lib/hooks';
import { useTema } from '../lib/tema';
import { Equipe } from '../lib/types';
import { Avatar, Cartao, Erro, Estado, Grupo, Icone, Subtitulo, Suave, Tela } from '../lib/ui';

/** Uma equipe dentro de um Grupo: iniciais, nome (e detalhe) e, à direita, a situação ou a ação. */
function LinhaDeEquipe({ equipe, detalhe, children }: { equipe: Equipe; detalhe?: string; children: ReactNode }) {
  const { cores } = useTema();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: cores.borda,
      }}>
      <Avatar nome={equipe.nome} />
      <View style={{ flex: 1, gap: 1 }}>
        <Text numberOfLines={1} style={{ fontSize: 16, fontWeight: '600', color: cores.texto }}>
          {equipe.nome}
        </Text>
        {!!detalhe && <Suave style={{ fontSize: 13 }}>{detalhe}</Suave>}
      </View>
      {children}
    </View>
  );
}

/** Situação ou ação no canto da linha (ícone + texto curto); com `aoTocar` vira botão. */
function Canto({
  icone,
  texto,
  cor,
  aoTocar,
  carregando,
}: {
  icone: Icone;
  texto: string;
  cor: string;
  aoTocar?: () => void;
  carregando?: boolean;
}) {
  if (carregando) return <ActivityIndicator size="small" color={cor} />;
  const conteudo = (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
      <Ionicons name={icone} size={16} color={cor} />
      <Text style={{ fontSize: 14, fontWeight: '600', color: cor }}>{texto}</Text>
    </View>
  );
  if (!aoTocar) return conteudo;
  return (
    <Pressable onPress={aoTocar} hitSlop={10} accessibilityRole="button" style={({ pressed }) => pressed && { opacity: 0.5 }}>
      {conteudo}
    </Pressable>
  );
}

export default function Equipes() {
  const equipes = useEquipes();
  const candidatura = useCandidatura();
  const ocupada = (equipe: Equipe) => candidatura.isPending && candidatura.variables?.equipeId === equipe.id;
  const dados = equipes.data;
  const { cores } = useTema();

  function pedirParaEntrar(equipe: Equipe) {
    Alert.alert(equipe.nome, 'Pedir para entrar nesta equipe? A liderança vai analisar seu pedido.', [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Pedir para entrar', onPress: () => candidatura.mutate({ equipeId: equipe.id }) },
    ]);
  }

  function cancelarPedido(equipe: Equipe) {
    Alert.alert(equipe.nome, 'Cancelar o pedido para entrar nesta equipe?', [
      { text: 'Voltar', style: 'cancel' },
      {
        text: 'Cancelar pedido',
        style: 'destructive',
        onPress: () => candidatura.mutate({ equipeId: equipe.id, cancelar: true }),
      },
    ]);
  }

  const participo = dados?.aprovadas.length ?? 0;

  return (
    <Tela aoAtualizar={() => equipes.refetch()}>
      <Estado consulta={equipes} />
      {dados && (
        <>
          <Cartao style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
            <View
              style={{
                width: 56,
                height: 56,
                borderRadius: 28,
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: cores.primaria,
              }}>
              <Ionicons name="people" size={26} color={cores.sobrePrimaria} />
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <Subtitulo>
                {participo === 0
                  ? 'Nenhuma equipe ainda'
                  : participo === 1
                    ? 'Você serve em 1 equipe'
                    : `Você serve em ${participo} equipes`}
              </Subtitulo>
              <Suave>Para entrar em outra, peça abaixo e aguarde a liderança aprovar.</Suave>
            </View>
          </Cartao>

          <Erro erro={candidatura.error} />

          <Grupo titulo="Participo">
            {dados.aprovadas.length === 0 ? (
              <View style={{ padding: 16, borderBottomWidth: 1, borderBottomColor: cores.borda }}>
                <Suave>Você ainda não participa de nenhuma equipe.</Suave>
              </View>
            ) : (
              dados.aprovadas.map((equipe) => (
                <LinhaDeEquipe key={equipe.id} equipe={equipe}>
                  <Canto icone="checkmark-circle" texto="Membro" cor={cores.confirmada} />
                </LinhaDeEquipe>
              ))
            )}
          </Grupo>

          {dados.pendentes.length > 0 && (
            <Grupo titulo="Aguardando aprovação">
              {dados.pendentes.map((equipe) => (
                <LinhaDeEquipe key={equipe.id} equipe={equipe} detalhe="Pedido enviado à liderança">
                  <Canto
                    icone="close-circle-outline"
                    texto="Cancelar"
                    cor={cores.perigo}
                    carregando={ocupada(equipe)}
                    aoTocar={() => cancelarPedido(equipe)}
                  />
                </LinhaDeEquipe>
              ))}
            </Grupo>
          )}

          {dados.disponiveis.length > 0 && (
            <Grupo titulo="Outras equipes">
              {dados.disponiveis.map((equipe) => (
                <LinhaDeEquipe key={equipe.id} equipe={equipe}>
                  <Canto
                    icone="add-circle-outline"
                    texto="Pedir para entrar"
                    cor={cores.primaria}
                    carregando={ocupada(equipe)}
                    aoTocar={() => pedirParaEntrar(equipe)}
                  />
                </LinhaDeEquipe>
              ))}
            </Grupo>
          )}
        </>
      )}
    </Tela>
  );
}
