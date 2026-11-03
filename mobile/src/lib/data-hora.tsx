import Ionicons from '@expo/vector-icons/Ionicons';
import DateTimePicker, { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { useState } from 'react';
import { Platform, Pressable, Text, View } from 'react-native';

import { useTema } from './tema';
import { Botao, Rotulo } from './ui';

type Modo = 'date' | 'time';

const TEXTO: Record<Modo, (d: Date) => string> = {
  date: (d) => format(d, 'EEEE, dd/MM/yyyy', { locale: ptBR }),
  time: (d) => format(d, 'HH:mm'),
};

/**
 * Campo de data ou hora com o seletor nativo (já incluído no app das lojas, então vale pelo ar).
 * Android abre o diálogo do sistema; iPhone mostra o seletor embaixo do campo, com "Pronto".
 */
export function CampoDeDataHora({
  rotulo,
  valor,
  modo,
  minimo,
  aoMudar,
}: {
  rotulo: string;
  valor: Date;
  modo: Modo;
  minimo?: Date;
  aoMudar: (data: Date) => void;
}) {
  const { cores, escuro } = useTema();
  const [aberto, setAberto] = useState(false);

  function abrir() {
    if (Platform.OS === 'android') {
      DateTimePickerAndroid.open({
        value: valor,
        mode: modo,
        is24Hour: true,
        minimumDate: minimo,
        onValueChange: (_evento, data) => aoMudar(data),
      });
    } else {
      setAberto((a) => !a);
    }
  }

  const texto = TEXTO[modo](valor);
  return (
    <View style={{ gap: 4 }}>
      <Rotulo>{rotulo}</Rotulo>
      <Pressable
        onPress={abrir}
        accessibilityRole="button"
        accessibilityLabel={`${rotulo}: ${texto}`}
        style={({ pressed }) => ({
          flexDirection: 'row',
          alignItems: 'center',
          gap: 10,
          minHeight: 48,
          paddingHorizontal: 14,
          borderWidth: 1,
          borderRadius: 10,
          borderColor: aberto ? cores.primaria : cores.borda,
          backgroundColor: cores.cartao,
          opacity: pressed ? 0.7 : 1,
        })}>
        <Ionicons name={modo === 'date' ? 'calendar-outline' : 'time-outline'} size={18} color={cores.primaria} />
        <Text style={{ flex: 1, fontSize: 16, color: cores.texto }}>{texto.charAt(0).toUpperCase() + texto.slice(1)}</Text>
        <Ionicons name={aberto ? 'chevron-up' : 'chevron-down'} size={16} color={cores.textoSuave} />
      </Pressable>
      {aberto && Platform.OS === 'ios' && (
        <View style={{ gap: 6 }}>
          <DateTimePicker
            value={valor}
            mode={modo}
            display={modo === 'date' ? 'inline' : 'spinner'}
            locale="pt-BR"
            minimumDate={minimo}
            accentColor={cores.primaria}
            themeVariant={escuro ? 'dark' : 'light'}
            onValueChange={(_evento, data) => aoMudar(data)}
          />
          <Botao titulo="Pronto" variante="secundario" aoTocar={() => setAberto(false)} />
        </View>
      )}
    </View>
  );
}

/** Mesmo dia de `dia`, no horário de `hora`. */
export function juntar(dia: Date, hora: Date) {
  const d = new Date(dia);
  d.setHours(hora.getHours(), hora.getMinutes(), 0, 0);
  return d;
}
