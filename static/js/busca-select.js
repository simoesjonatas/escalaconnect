/*
 * Transforma qualquer <select data-busca> em um campo de busca com lista filtrável,
 * para listas longas (membros, usuários). O <select> original fica oculto e continua
 * sendo o valor enviado no formulário; esta camada só facilita a escolha.
 *
 * Uso: <select name="usuario" data-busca> ... </select> + incluir este arquivo.
 * Estilos: .busca-select-* em theme.css.
 */
(function () {
  const normalizar = (t) => (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

  function montar(select) {
    const opcoes = Array.from(select.options).filter((o) => o.value !== '');
    const placeholderOpt = Array.from(select.options).find((o) => o.value === '');

    const caixa = document.createElement('div');
    caixa.className = 'busca-select';

    const campo = document.createElement('input');
    campo.type = 'search';
    campo.className = 'form-control busca-select-campo';
    campo.autocomplete = 'off';
    campo.placeholder = select.dataset.buscaPlaceholder || 'Digite para buscar…';
    campo.setAttribute('aria-label', select.dataset.buscaRotulo || 'Buscar');

    const lista = document.createElement('div');
    lista.className = 'busca-select-lista';
    lista.setAttribute('role', 'listbox');

    const itens = opcoes.map((opt) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'busca-select-item';
      item.setAttribute('role', 'option');
      item.dataset.valor = opt.value;
      item.dataset.busca = normalizar(opt.text);
      const inicial = document.createElement('span');
      inicial.className = 'busca-select-inicial';
      inicial.textContent = opt.text.trim().charAt(0).toUpperCase();
      const nome = document.createElement('span');
      nome.textContent = opt.text;
      item.append(inicial, nome);
      item.addEventListener('click', () => escolher(item));
      lista.appendChild(item);
      return item;
    });

    const vazio = document.createElement('div');
    vazio.className = 'busca-select-vazio';
    vazio.textContent = select.dataset.buscaVazio || 'Nenhum resultado.';
    vazio.hidden = true;
    lista.appendChild(vazio);

    function filtrar() {
      const termo = normalizar(campo.value);
      let visiveis = 0;
      itens.forEach((item) => {
        const mostra = !termo || item.dataset.busca.includes(termo);
        item.hidden = !mostra;
        if (mostra) visiveis++;
      });
      vazio.hidden = visiveis > 0;
    }

    function marcar(valor) {
      itens.forEach((i) => {
        const sel = i.dataset.valor === valor;
        i.classList.toggle('selecionado', sel);
        i.setAttribute('aria-selected', sel ? 'true' : 'false');
      });
    }

    function escolher(item) {
      select.value = item.dataset.valor;
      select.dispatchEvent(new Event('change', { bubbles: true }));
      campo.value = item.lastChild.textContent;
      marcar(item.dataset.valor);
      filtrar();
    }

    campo.addEventListener('input', () => {
      // Digitar de novo desfaz a escolha, para não enviar um valor que não bate com o texto.
      select.value = placeholderOpt ? '' : select.value;
      marcar(select.value);
      filtrar();
    });
    campo.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault(); // Enter escolhe o primeiro da lista em vez de enviar o formulário
      const primeiro = itens.find((i) => !i.hidden);
      if (primeiro) escolher(primeiro);
    });

    // Valor já selecionado (edição ou formulário devolvido com erro).
    const atual = itens.find((i) => i.dataset.valor === select.value);
    if (atual) {
      campo.value = atual.lastChild.textContent;
      marcar(select.value);
    }

    select.hidden = true;
    select.setAttribute('aria-hidden', 'true');
    select.tabIndex = -1;
    caixa.append(campo, lista);
    select.insertAdjacentElement('afterend', caixa);
    filtrar();
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('select[data-busca]').forEach(montar);
  });
})();
