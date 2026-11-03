import base64

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core import signing
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import reverse
from django.shortcuts import get_object_or_404
from .models import Equipe
from escala.models import Escala
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.timezone import make_aware
from equipe.decorators import pode_gerenciar_equipe, require_lideranca
from io import BytesIO

# Whitelist: nunca renderizar nome de template vindo direto do POST
PDF_TEMPLATES = {
    'connect': 'pdf/escala_connect.html',
    'escuro': 'pdf/escala_escuro.html',
    'mural': 'pdf/escala_mural.html',
}


def _logo_data_uri():
    caminho = finders.find('images/logo_connect.JPG')
    if not caminho:
        return ''
    with open(caminho, 'rb') as arquivo:
        return 'data:image/jpeg;base64,' + base64.b64encode(arquivo.read()).decode('ascii')


def _pdf_com_reportlab(equipe, escalas, mes_nome, ano):
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError("ReportLab nao esta instalado. Rode: pip install reportlab") from exc

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "EscalaTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        spaceAfter=10,
    )
    small_style = ParagraphStyle(
        "EscalaSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    )

    story = [
        Paragraph(f"Escala {equipe.nome} - {mes_nome}/{ano}", title_style),
        Spacer(1, 8),
    ]

    data = [["Data", "Evento", "Função", "Voluntário", "Status"]]
    for escala in escalas:
        if escala.usuario:
            usuario = escala.usuario.get_full_name() or escala.usuario.username
        else:
            usuario = "Vaga em aberto"
        status = "Confirmada" if escala.confirmada else "A confirmar"
        data.append([
            timezone.localtime(escala.evento.data_inicio).strftime("%d/%m/%Y %H:%M"),
            Paragraph(escala.evento.nome, small_style),
            Paragraph(escala.funcao.nome, small_style),
            Paragraph(usuario, small_style),
            status,
        ])

    if len(data) == 1:
        data.append(["-", "Nenhuma escala encontrada para este mês.", "-", "-", "-"])

    table = Table(data, colWidths=[3.2 * cm, 7.0 * cm, 5.0 * cm, 5.2 * cm, 3.0 * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16202e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c9d1d9")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f8")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)

    doc.build(story)
    return buffer.getvalue()


MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto',
         'Setembro', 'Outubro', 'Novembro', 'Dezembro']


class PdfIndisponivel(RuntimeError):
    """Nem WeasyPrint nem ReportLab conseguiram gerar o PDF."""


def pdf_da_escala(equipe, ano, mes, estilo='connect', base_url=None):
    """PDF da escala da equipe no mês (mesmo do botão "Exportar PDF" do site).

    Devolve (bytes do PDF, nome do arquivo). `estilo` é uma chave de PDF_TEMPLATES.
    """
    mes_nome = MESES[mes - 1]
    inicio_mes = make_aware(datetime(ano, mes, 1))
    fim_mes = make_aware(datetime(ano + (mes == 12), mes % 12 + 1, 1)) - timedelta(seconds=1)

    # Escalas do mês, ordenadas para o agrupamento por evento no template.
    escalas = list(
        Escala.objects
        .filter(
            funcao__equipe=equipe,
            evento__data_inicio__gte=inicio_mes,
            evento__data_inicio__lte=fim_mes,
        )
        .select_related('evento', 'funcao', 'usuario')
        .order_by('evento__data_inicio', 'evento_id', 'funcao__nome')
    )

    template_html = PDF_TEMPLATES.get(estilo, PDF_TEMPLATES['connect'])
    contexto = {
        'escalas': escalas,
        'equipe': equipe,
        'mes_nome': mes_nome,
        'ano': ano,
        'gerado_em': timezone.localtime(),
        'logo_data_uri': _logo_data_uri(),
        'total': len(escalas),
        'confirmadas': sum(1 for e in escalas if e.usuario_id and e.confirmada),
        'pendentes': sum(1 for e in escalas if e.usuario_id and not e.confirmada),
        'vagas': sum(1 for e in escalas if not e.usuario_id),
    }

    try:
        from weasyprint import HTML
        html_string = render_to_string(template_html, contexto)
        pdf = HTML(string=html_string, base_url=base_url).write_pdf()
    except (ImportError, OSError, RuntimeError):
        try:
            pdf = _pdf_com_reportlab(equipe, escalas, mes_nome, ano)
        except RuntimeError as exc:
            raise PdfIndisponivel(str(exc)) from exc
    return pdf, f'escala_{equipe.nome}_{mes_nome}_{ano}.pdf'


@require_lideranca
def exportar_tabela_para_pdf(request, equipe_pk):
    if request.method != 'POST':
        return HttpResponse("Método não suportado", status=405)
    equipe = get_object_or_404(Equipe, pk=equipe_pk)

    # Mês escolhido; se já passou neste ano, é o do ano que vem.
    hoje = datetime.now()
    mes_escolhido = request.POST.get('mes')
    mes = int(mes_escolhido) if mes_escolhido else hoje.month
    ano = hoje.year if mes >= hoje.month else hoje.year + 1

    try:
        pdf, nome = pdf_da_escala(equipe, ano, mes, request.POST.get('template'),
                                  base_url=request.build_absolute_uri('/'))
    except PdfIndisponivel as exc:
        return HttpResponse(str(exc), status=503, content_type="text/plain; charset=utf-8")

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nome}"'
    return response


# ── Link do PDF para o app do líder ──
# O app não tem sessão do site: a API devolve um link assinado e temporário, que abre o
# PDF no navegador do celular (de lá a pessoa salva ou compartilha).

SALT_PDF = 'escala-connect.pdf-da-escala'
VALIDADE_DO_LINK = 60 * 60  # 1 hora


def link_do_pdf(usuario, equipe, ano, mes, estilo):
    token = signing.dumps({'u': usuario.pk, 'e': equipe.pk, 'a': ano, 'm': mes, 's': estilo},
                          salt=SALT_PDF, compress=True)
    return settings.SITE_URL + reverse('pdf_da_escala', args=[token])


def pdf_por_link(request, token):
    # 404 direto: o handler404 do site redirecionaria para a página inicial.
    invalido = HttpResponseNotFound('Link do PDF inválido ou expirado. Gere de novo pelo app.')
    try:
        dados = signing.loads(token, salt=SALT_PDF, max_age=VALIDADE_DO_LINK)
    except signing.BadSignature:  # inclui o link expirado
        return invalido
    usuario = get_user_model().objects.filter(pk=dados.get('u'), is_active=True).first()
    equipe = Equipe.objects.filter(pk=dados.get('e')).first()
    # Quem deixou de liderar a equipe não baixa mais pelo link antigo.
    if usuario is None or equipe is None or not pode_gerenciar_equipe(usuario, equipe):
        return invalido
    try:
        pdf, nome = pdf_da_escala(equipe, dados['a'], dados['m'], dados.get('s'),
                                  base_url=request.build_absolute_uri('/'))
    except PdfIndisponivel as exc:
        return HttpResponse(str(exc), status=503, content_type="text/plain; charset=utf-8")
    response = HttpResponse(pdf, content_type='application/pdf')
    # inline: o navegador do celular mostra o PDF e oferece salvar/compartilhar.
    response['Content-Disposition'] = f'inline; filename="{nome}"'
    return response
