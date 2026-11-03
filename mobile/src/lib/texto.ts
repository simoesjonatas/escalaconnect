/** Para buscas: sem acento e em minúsculas ("Câmera" acha "camera"). */
export const semAcento = (texto: string) =>
  texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

/** Todas as palavras digitadas aparecem no texto, em qualquer ordem. */
export const contemTudo = (texto: string, busca: string) => {
  const alvo = semAcento(texto);
  return semAcento(busca).split(/\s+/).filter(Boolean).every((parte) => alvo.includes(parte));
};
