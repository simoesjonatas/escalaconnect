import { endOfMonth, format, startOfMonth } from 'date-fns';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable } from 'react-native';
import { Calendar, LocaleConfig } from 'react-native-calendars';

import { chaveDoDia, diaPorExtenso, hora } from '../../lib/datas';
import { useEscalas, useEventos } from '../../lib/hooks';
import { Cores, useTema } from '../../lib/tema';
import { EventoCalendario } from '../../lib/types';
import { Cartao, Estado, Etiqueta, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

LocaleConfig.locales['pt-br'] = {
  monthNames: [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
  ],
  monthNamesShort: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
  dayNames: ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'],
  dayNamesShort: ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'],
  today: 'Hoje',
};
LocaleConfig.defaultLocale = 'pt-br';

// Mesmas cores do calendário do site: verde confirmada, laranja a confirmar, azul sem escala.
const corDoEvento = (e: EventoCalendario, cores: Cores) =>
  e.escalado ? (e.confirmada ? cores.confirmada : cores.pendente) : cores.neutra;

export default function Calendario() {
  const [mes, setMes] = useState(() => startOfMonth(new Date()));
  const [dia, setDia] = useState(() => chaveDoDia(new Date()));
  const eventos = useEventos(format(mes, 'yyyy-MM-dd'), format(endOfMonth(mes), 'yyyy-MM-dd'));
  const escalas = useEscalas();
  const { cores, escuro } = useTema();

  const porDia = useMemo(() => {
    const mapa: Record<string, EventoCalendario[]> = {};
    for (const evento of eventos.data ?? []) (mapa[chaveDoDia(evento.data_inicio)] ??= []).push(evento);
    return mapa;
  }, [eventos.data]);

  const marcacoes = useMemo(() => {
    const marcas: Record<string, object> = {};
    for (const [chave, doDia] of Object.entries(porDia)) {
      // Um ponto por cor presente no dia.
      const dots = [...new Set(doDia.map((e) => corDoEvento(e, cores)))].map((color) => ({ key: color, color }));
      marcas[chave] = { dots };
    }
    marcas[dia] = { ...marcas[dia], selected: true, selectedColor: cores.primaria };
    return marcas;
  }, [porDia, dia, cores]);

  function abrir(evento: EventoCalendario) {
    // Evento em que estou escalado abre a minha escala.
    const escala = escalas.data?.find((e) => e.evento.id === evento.id);
    if (escala) router.push({ pathname: '/escala/[id]', params: { id: escala.id } });
  }

  const doDia = porDia[dia] ?? [];
  return (
    <Tela atualizando={eventos.isRefetching} aoAtualizar={() => eventos.refetch()}>
      <Calendar
        markingType="multi-dot"
        markedDates={marcacoes}
        onDayPress={(d) => setDia(d.dateString)}
        onMonthChange={(m) => setMes(new Date(m.year, m.month - 1, 1))}
        key={escuro ? 'escuro' : 'claro'} // o calendário não reaplica o tema sem remontar
        theme={{
          calendarBackground: cores.cartao,
          dayTextColor: cores.texto,
          monthTextColor: cores.texto,
          textSectionTitleColor: cores.textoSuave,
          textDisabledColor: cores.borda,
          todayTextColor: cores.primaria,
          arrowColor: cores.primaria,
          selectedDayTextColor: cores.sobrePrimaria,
        }}
        style={{ borderRadius: 12, borderWidth: 1, borderColor: cores.borda }}
      />
      <Subtitulo>{diaPorExtenso(`${dia}T12:00:00`)}</Subtitulo>
      <Estado consulta={eventos} vazio={doDia.length === 0 && 'Nenhum evento neste dia.'} />
      {doDia.map((evento) => (
        <Pressable key={evento.id} onPress={() => abrir(evento)} disabled={!evento.escalado}>
          <Cartao>
            {evento.escalado && (
              <Etiqueta texto={evento.confirmada ? 'Confirmada' : 'A confirmar'} cor={corDoEvento(evento, cores)} />
            )}
            <Subtitulo>{evento.nome}</Subtitulo>
            <Texto>
              {hora(evento.data_inicio)} – {hora(evento.data_fim)}
            </Texto>
            {evento.escalado && <Suave>Você serve como: {evento.funcoes.join(', ')}</Suave>}
            {!!evento.equipe && <Suave>Evento da equipe {evento.equipe}</Suave>}
          </Cartao>
        </Pressable>
      ))}
    </Tela>
  );
}
