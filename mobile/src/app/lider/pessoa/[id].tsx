import Ionicons from '@expo/vector-icons/Ionicons';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { Alert, Pressable, Text, View } from 'react-native';

import { diaCurto } from '../../../lib/datas';
import { useEscalar, useEscolhasDaPessoa } from '../../../lib/hooks';
import { useTema } from '../../../lib/tema';
import { EscolhaDaPessoa, VagaDaPessoa } from '../../../lib/types';
import { Cartao, Erro, Estado, Etiqueta, Suave, Subtitulo, Tela, Texto } from '../../../lib/ui';

/**
 * Dias que a pessoa escolheu nos próximos 60 dias (marcou disponibilidade ou se ofereceu numa
 * vaga), com as vagas abertas das equipes do líder em cada um: tocar numa vaga escala a pessoa.
 */
export default function DiasDaPessoa() {
  const id = Number(useLocalSearchParams<{ id: string }>().id);
  const consulta = useEscolhasDaPessoa(id);
  const escalar = useEscalar();
  const { cores } = useTema();
  const dados = consulta.data;
  const nome = dados?.pessoa.nome ?? '';
  const primeiroNome = nome.split(' ')[0];

  function confirmar(escolha: EscolhaDaPessoa, vaga: VagaDaPessoa) {
    const aviso = escolha.ja_escalado_em
      ? `\n\nJá está escalado neste evento: ${escolha.ja_escalado_em}. Vai servir nas duas funções.`
      : '';
    Alert.alert(
      'Escalar',
      `Escalar ${nome} em ${vaga.funcao} · ${escolha.evento.nome} (${diaCurto(escolha.evento.data_inicio)})? ` +
        `A pessoa recebe um aviso no app.${aviso}`,
      [
        { text: 'Voltar', style: 'cancel' },
        {
          text: 'Escalar',
          onPress: () =>
            escalar.mutate(
              { vagaId: vaga.id, usuarioId: id, mesmoEvento: !!escolha.ja_escalado_em },
              { onSuccess: () => Alert.alert('Pronto', `${nome} está na escala e recebeu um aviso no app.`) },
            ),
        },
      ],
    );
  }

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Stack.Screen options={{ title: nome ? `Dias de ${primeiroNome}` : 'Dias que marcou' }} />
      <Estado consulta={consulta} />
      {dados && (
        <>
          <Cartao>
            <Subtitulo>{nome}</Subtitulo>
            <Suave>
              {dados.servicos_no_mes === 0
                ? 'Ainda não serve neste mês'
                : `Já serve ${dados.servicos_no_mes}x neste mês`}
              {' · '}
              {dados.equipes.join(', ')}
            </Suave>
            <Texto>Dias em que marcou que pode servir ou se ofereceu numa vaga. Toque numa vaga para escalar.</Texto>
          </Cartao>

          <Erro erro={escalar.error} />

          {dados.eventos.length === 0 && (
            <Suave style={{ textAlign: 'center' }}>
              {primeiroNome} não marcou disponibilidade nem se ofereceu para nenhuma vaga nos próximos 60 dias.
            </Suave>
          )}

          {dados.eventos.map((escolha) => {
            const ofereceu = escolha.vagas.filter((v) => v.se_ofereceu).map((v) => v.funcao);
            return (
              <Cartao key={escolha.evento.id} style={{ gap: 8 }}>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                  {escolha.disponivel && <Etiqueta texto="Marcou que pode" cor={cores.confirmada} />}
                  {ofereceu.length > 0 && (
                    <Etiqueta texto={`Se ofereceu: ${ofereceu.join(', ')}`} cor={cores.primaria} />
                  )}
                  {!!escolha.ja_escalado_em && <Etiqueta texto="Já escalado" cor={cores.neutra} />}
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Subtitulo style={{ flex: 1 }}>{escolha.evento.nome}</Subtitulo>
                  {escolha.culto_da_equipe && (
                    <Pressable
                      onPress={() => abrirCulto(escolha.evento.id)}
                      hitSlop={10}
                      accessibilityRole="link"
                      accessibilityLabel={`Ver o culto ${escolha.evento.nome}`}
                      style={({ pressed }) => [
                        { flexDirection: 'row', alignItems: 'center', gap: 2 },
                        pressed && { opacity: 0.6 },
                      ]}>
                      <Text style={{ color: cores.primaria, fontSize: 14, fontWeight: '600' }}>Ver culto</Text>
                      <Ionicons name="chevron-forward" size={14} color={cores.primaria} />
                    </Pressable>
                  )}
                </View>
                <Suave>{diaCurto(escolha.evento.data_inicio)}</Suave>
                {!!escolha.ja_escalado_em && <Texto>Serve em {escolha.ja_escalado_em}</Texto>}
                {escolha.vagas.map((vaga) => (
                  <Pressable
                    key={vaga.id}
                    onPress={() => confirmar(escolha, vaga)}
                    disabled={escalar.isPending}
                    accessibilityRole="button"
                    accessibilityLabel={`Escalar em ${vaga.funcao}`}
                    style={({ pressed }) => [
                      {
                        flexDirection: 'row',
                        alignItems: 'center',
                        gap: 8,
                        paddingVertical: 10,
                        paddingHorizontal: 12,
                        borderRadius: 10,
                        borderWidth: 1,
                        borderColor: vaga.se_ofereceu ? cores.primaria : cores.borda,
                      },
                      (pressed || escalar.isPending) && { opacity: 0.6 },
                    ]}>
                    <View style={{ flex: 1, gap: 2 }}>
                      <Text style={{ color: cores.texto, fontSize: 15, fontWeight: '600' }}>
                        Vaga: {vaga.funcao}
                        {dados.equipes.length > 1 && (
                          <Text style={{ color: cores.textoSuave, fontWeight: '400' }}> · {vaga.equipe}</Text>
                        )}
                      </Text>
                      <Concorrencia vaga={vaga} />
                    </View>
                    <Text style={{ color: cores.primaria, fontSize: 15, fontWeight: '700' }}>Escalar</Text>
                    <Ionicons name="chevron-forward" size={16} color={cores.primaria} />
                  </Pressable>
                ))}
                {escolha.vagas.length === 0 && !escolha.ja_escalado_em && (
                  <Suave>Sem vaga aberta nas suas equipes</Suave>
                )}
              </Cartao>
            );
          })}
        </>
      )}
    </Tela>
  );
}

const abrirCulto = (id: number) => router.push({ pathname: '/lider/culto/[id]', params: { id } });

/**
 * Quantos outros (fora a pessoa) podem ocupar a vaga, somando quem quer servir e quem está
 * disponível: "+3 opções". Ninguém mais = "Única opção", em destaque. Servidor anterior não manda.
 */
function Concorrencia({ vaga }: { vaga: VagaDaPessoa }) {
  const { cores } = useTema();
  if (vaga.outros_querem === undefined) return null;
  const outros = vaga.outros_querem + vaga.outros_disponiveis;
  if (outros === 0) {
    return <Text style={{ color: cores.pendente, fontSize: 13, fontWeight: '600' }}>Única opção</Text>;
  }
  return (
    <Text style={{ color: cores.textoSuave, fontSize: 13 }}>
      +{outros} {outros === 1 ? 'opção' : 'opções'}
    </Text>
  );
}
