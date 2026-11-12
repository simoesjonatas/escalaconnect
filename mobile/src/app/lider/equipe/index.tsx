import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { ReactNode, useState } from 'react';
import { Alert, Pressable, Text, View } from 'react-native';

import { ChipsDeEscolha } from '../../../lib/formulario-lider';
import { MudancaNaEquipe, useEquipeDoLider, useMudarEquipe, useOpcoesDeEventos } from '../../../lib/hooks';
import { useTema } from '../../../lib/tema';
import {
  Avatar,
  Botao,
  Campo,
  Cartao,
  Erro,
  Estado,
  Grupo,
  Icone,
  ItemDeGrupo,
  Subtitulo,
  Suave,
  Tela,
} from '../../../lib/ui';

/** Linha de um Grupo com conteúdo livre à esquerda e uma ação curta à direita. */
function Linha({
  inicio,
  titulo,
  detalhe,
  acao,
  aoTocar,
}: {
  inicio: ReactNode;
  titulo: string;
  detalhe?: string;
  acao?: { texto: string; icone: Icone; perigo?: boolean; aoTocar: () => void };
  aoTocar?: () => void;
}) {
  const { cores } = useTema();
  return (
    <Pressable
      onPress={aoTocar}
      disabled={!aoTocar}
      style={({ pressed }) => ({
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: cores.borda,
        backgroundColor: pressed ? cores.fundo : undefined,
      })}>
      {inicio}
      <View style={{ flex: 1, gap: 1 }}>
        <Text numberOfLines={1} style={{ fontSize: 16, fontWeight: '600', color: cores.texto }}>
          {titulo}
        </Text>
        {!!detalhe && <Suave style={{ fontSize: 13 }}>{detalhe}</Suave>}
      </View>
      {acao && (
        <Pressable
          onPress={acao.aoTocar}
          hitSlop={10}
          accessibilityRole="button"
          style={{ flexDirection: 'row', gap: 4 }}>
          <Ionicons name={acao.icone} size={16} color={acao.perigo ? cores.perigo : cores.primaria} />
          <Text style={{ fontSize: 14, fontWeight: '600', color: acao.perigo ? cores.perigo : cores.primaria }}>
            {acao.texto}
          </Text>
        </Pressable>
      )}
      {!acao && aoTocar && <Ionicons name="chevron-forward" size={18} color={cores.textoSuave} />}
    </Pressable>
  );
}

type Edicao = { tipo: 'equipe' | 'nova-funcao' | 'funcao'; id?: number; nome: string; escalas?: number };

/**
 * Gerenciar a equipe, com os mesmos papéis do site: o líder mexe em funções e integrantes e
 * remove lideranças. Trocar o nome é só do admin; adicionar líder continua pelo site (admin).
 */
export default function GerenciarEquipe() {
  const opcoes = useOpcoesDeEventos();
  const [escolhida, setEscolhida] = useState<number>();
  const equipeId = escolhida ?? opcoes.data?.equipes[0]?.id;
  const consulta = useEquipeDoLider(equipeId);
  const mudar = useMudarEquipe();
  const { cores } = useTema();
  const [edicao, setEdicao] = useState<Edicao | null>(null);
  const dados = consulta.data;

  function executar(mudanca: MudancaNaEquipe, depois?: () => void) {
    mudar.mutate(mudanca, { onSuccess: () => depois?.() });
  }

  function confirmar(titulo: string, texto: string, botao: string, mudanca: MudancaNaEquipe) {
    Alert.alert(titulo, texto, [
      { text: 'Voltar', style: 'cancel' },
      { text: botao, style: 'destructive', onPress: () => executar(mudanca) },
    ]);
  }

  function salvarEdicao() {
    if (!edicao || !equipeId) return;
    const nome = edicao.nome.trim();
    const mudanca: MudancaNaEquipe =
      edicao.tipo === 'equipe'
        ? { tipo: 'renomear-equipe', equipeId, nome }
        : edicao.tipo === 'nova-funcao'
          ? { tipo: 'criar-funcao', equipeId, nome }
          : { tipo: 'renomear-funcao', id: edicao.id!, nome };
    executar(mudanca, () => setEdicao(null));
  }

  function excluirFuncao() {
    if (!edicao?.id) return;
    if (edicao.escalas) {
      Alert.alert(
        'Não dá para excluir',
        `${edicao.nome} já tem ${edicao.escalas} escala${edicao.escalas === 1 ? '' : 's'}. Para não perder o histórico de quem serviu, peça ao admin para excluir.`,
      );
      return;
    }
    const id = edicao.id;
    Alert.alert('Excluir função', `Excluir ${edicao.nome}?`, [
      { text: 'Voltar', style: 'cancel' },
      {
        text: 'Excluir',
        style: 'destructive',
        onPress: () => executar({ tipo: 'excluir-funcao', id }, () => setEdicao(null)),
      },
    ]);
  }

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Estado consulta={opcoes} vazio={opcoes.data?.equipes.length === 0 && 'Você não lidera nenhuma equipe.'} />
      {opcoes.data && opcoes.data.equipes.length > 1 && (
        <Cartao>
          <ChipsDeEscolha
            titulo="Equipe"
            opcoes={opcoes.data.equipes.map((e) => ({ valor: e.id, rotulo: e.nome }))}
            ativas={equipeId ? [equipeId] : []}
            aoTocar={(id) => {
              setEscolhida(id);
              setEdicao(null);
            }}
          />
        </Cartao>
      )}
      {equipeId && <Estado consulta={consulta} />}

      {dados && (
        <>
          <Cartao style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
            <Avatar nome={dados.nome} tamanho={48} destaque />
            <View style={{ flex: 1, gap: 2 }}>
              <Subtitulo>{dados.nome}</Subtitulo>
              <Suave>
                {dados.integrantes.length} integrante{dados.integrantes.length === 1 ? '' : 's'} ·{' '}
                {dados.funcoes.length} funç{dados.funcoes.length === 1 ? 'ão' : 'ões'}
              </Suave>
            </View>
            {dados.pode_renomear && (
              <Pressable onPress={() => setEdicao({ tipo: 'equipe', nome: dados.nome })} hitSlop={10}>
                <Ionicons name="create-outline" size={22} color={cores.primaria} />
              </Pressable>
            )}
          </Cartao>

          {edicao && (
            <Cartao style={{ gap: 12, borderColor: cores.primaria }}>
              <Campo
                rotulo={
                  edicao.tipo === 'equipe'
                    ? 'Nome da equipe'
                    : edicao.tipo === 'nova-funcao'
                      ? 'Nova função'
                      : 'Nome da função'
                }
                value={edicao.nome}
                onChangeText={(nome) => setEdicao({ ...edicao, nome })}
                autoFocus
                placeholder={edicao.tipo === 'nova-funcao' ? 'Ex.: Câmera 2' : undefined}
              />
              <Erro erro={mudar.error} />
              <Botao
                titulo="Salvar"
                desabilitado={!edicao.nome.trim()}
                carregando={mudar.isPending}
                aoTocar={salvarEdicao}
              />
              {edicao.tipo === 'funcao' && <Botao titulo="Excluir função" variante="perigo" aoTocar={excluirFuncao} />}
              <Botao titulo="Cancelar" variante="secundario" aoTocar={() => setEdicao(null)} />
            </Cartao>
          )}
          {!edicao && <Erro erro={mudar.error} />}

          <Grupo titulo="Funções">
            {dados.funcoes.map((f) => (
              <Linha
                key={f.id}
                inicio={<Ionicons name="layers-outline" size={20} color={cores.primaria} />}
                titulo={f.nome}
                detalhe={f.escalas ? `${f.escalas} escala${f.escalas === 1 ? '' : 's'}` : 'Sem escalas'}
                aoTocar={() => setEdicao({ tipo: 'funcao', id: f.id, nome: f.nome, escalas: f.escalas })}
              />
            ))}
            <ItemDeGrupo
              icone="add-circle-outline"
              titulo="Nova função"
              aoTocar={() => setEdicao({ tipo: 'nova-funcao', nome: '' })}
            />
          </Grupo>

          <Grupo titulo="Líderes">
            {dados.lideres.map((l) => (
              <Linha
                key={l.id}
                inicio={<Avatar nome={l.pessoa.nome} />}
                titulo={l.sou_eu ? `${l.pessoa.nome} (você)` : l.pessoa.nome}
                acao={
                  dados.lideres.length > 1
                    ? {
                        texto: 'Remover',
                        icone: 'close-circle-outline',
                        perigo: true,
                        aoTocar: () =>
                          confirmar(
                            'Remover liderança',
                            l.sou_eu
                              ? 'Você deixa de ser líder desta equipe e perde o acesso às ferramentas dela.'
                              : `${l.pessoa.nome} deixa de ser líder (continua na equipe).`,
                            'Remover',
                            { tipo: 'remover-lider', id: l.id },
                          ),
                      }
                    : undefined
                }
              />
            ))}
            <View style={{ padding: 16, borderBottomWidth: 1, borderBottomColor: cores.borda }}>
              <Suave style={{ fontSize: 13 }}>Para adicionar um líder, fale com o admin.</Suave>
            </View>
          </Grupo>

          <Grupo titulo={`Integrantes (${dados.integrantes.length}) · toque para ver os dias que marcou`}>
            <ItemDeGrupo
              icone="person-add-outline"
              titulo="Adicionar integrante"
              aoTocar={() => router.push({ pathname: '/lider/equipe/adicionar', params: { equipe: dados.id } })}
            />
            {dados.pendentes.length > 0 && (
              <View style={{ padding: 16, borderBottomWidth: 1, borderBottomColor: cores.borda }}>
                <Suave style={{ fontSize: 13, color: cores.pendente }}>
                  {dados.pendentes.length === 1
                    ? `${dados.pendentes[0].pessoa.nome} pediu para entrar. Aprove em Pendências.`
                    : `${dados.pendentes.length} pessoas pediram para entrar. Aprove em Pendências.`}
                </Suave>
              </View>
            )}
            {dados.integrantes.map((i) => (
              <Linha
                key={i.id}
                inicio={<Avatar nome={i.pessoa.nome} />}
                titulo={i.pessoa.nome}
                aoTocar={() => router.push({ pathname: '/lider/pessoa/[id]', params: { id: i.pessoa.id } })}
                detalhe={
                  i.lider
                    ? 'Líder'
                    : i.escalas_futuras
                      ? `${i.escalas_futuras} escala${i.escalas_futuras === 1 ? '' : 's'} pela frente`
                      : undefined
                }
                acao={
                  i.lider
                    ? undefined
                    : {
                        texto: 'Remover',
                        icone: 'close-circle-outline',
                        perigo: true,
                        aoTocar: () =>
                          confirmar(
                            'Remover da equipe',
                            `${i.pessoa.nome} sai da equipe ${dados.nome}.` +
                              (i.escalas_futuras
                                ? ` As ${i.escalas_futuras} escala${i.escalas_futuras === 1 ? '' : 's'} já marcada${i.escalas_futuras === 1 ? '' : 's'} continua${i.escalas_futuras === 1 ? '' : 'm'}; troque a pessoa no culto se precisar.`
                                : ''),
                            'Remover',
                            { tipo: 'remover-integrante', id: i.id },
                          ),
                      }
                }
              />
            ))}
          </Grupo>
        </>
      )}
    </Tela>
  );
}
