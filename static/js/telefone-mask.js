// Máscara automática de telefone BR para todos os campos input[type="tel"].
// Formata enquanto digita: (21) 99276-9489. O servidor normaliza de qualquer
// forma (usuario.utils.normalizar_telefone), então isto é só conforto visual.
document.addEventListener('DOMContentLoaded', function () {
    function mascarar(valor) {
        let d = valor.replace(/\D/g, '');
        if (d.length > 11 && d.startsWith('55')) d = d.slice(2); // remove +55 colado
        d = d.slice(0, 11);
        if (!d) return '';
        if (d.length <= 2) return '(' + d;
        if (d.length <= 6) return '(' + d.slice(0, 2) + ') ' + d.slice(2);
        if (d.length <= 10) return '(' + d.slice(0, 2) + ') ' + d.slice(2, 6) + '-' + d.slice(6);
        return '(' + d.slice(0, 2) + ') ' + d.slice(2, 7) + '-' + d.slice(7);
    }

    document.querySelectorAll('input[type="tel"]').forEach(function (campo) {
        campo.maxLength = 16; // "(21) 99999-9999" tem 15 caracteres
        campo.addEventListener('input', function () {
            campo.value = mascarar(campo.value);
        });
        // Formata o valor já salvo (vem do banco só com dígitos).
        campo.value = mascarar(campo.value);
    });
});
