from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import Equipe
from escala.models import Escala
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from equipe.decorators import require_lideranca
from io import BytesIO


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
            escala.evento.data_inicio.strftime("%d/%m/%Y %H:%M"),
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


@require_lideranca
def exportar_tabela_para_pdf(request, equipe_pk):
    if request.method == 'POST':
        equipe = get_object_or_404(Equipe, pk=equipe_pk)
        ano_atual = datetime.now().year
        
        
        # Dicionário de nomes de meses
        meses = {
            1: 'Janeiro',
            2: 'Fevereiro',
            3: 'Março',
            4: 'Abril',
            5: 'Maio',
            6: 'Junho',
            7: 'Julho',
            8: 'Agosto',
            9: 'Setembro',
            10: 'Outubro',
            11: 'Novembro',
            12: 'Dezembro'
        }

        # Capturando o mês a partir do POST
        mes_escolhido = request.POST.get('mes')
        mes = int(mes_escolhido) if mes_escolhido else datetime.now().month
        mes_nome = meses[mes]

        # Decidir o ano baseado no mês selecionado
        ano = ano_atual if mes >= datetime.now().month else ano_atual + 1

        # Determinar o início e o fim do mês selecionado
        inicio_mes = make_aware(datetime(ano, mes, 1))
        if mes == 12:
            fim_mes = make_aware(datetime(ano + 1, 1, 1)) - timedelta(seconds=1)
        else:
            fim_mes = make_aware(datetime(ano, mes + 1, 1)) - timedelta(seconds=1)

        # Filtrar escalas pelo mês e ano
        escalas = (
            Escala.objects
            .filter(
                funcao__equipe_id=equipe_pk,
                evento__data_inicio__gte=inicio_mes,
                evento__data_inicio__lte=fim_mes,
            )
            .select_related('evento', 'funcao', 'usuario')
            .order_by('evento__data_inicio')
        )

        try:
            from weasyprint import HTML
            html_string = render_to_string('meu_template.html', {'escalas': escalas, 'equipe': equipe, 'mes_nome': mes_nome})
            html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
            pdf = html.write_pdf()
        except (ImportError, OSError, RuntimeError):
            try:
                pdf = _pdf_com_reportlab(equipe, escalas, mes_nome, ano)
            except RuntimeError as exc:
                return HttpResponse(str(exc), status=503, content_type="text/plain; charset=utf-8")

        # Nome do arquivo personalizado com nome da equipe e mês
        nome_mes = inicio_mes.strftime('%B').capitalize()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="escala_{equipe.nome}_{nome_mes}_{ano}.pdf"'

        return response
    else:
        # Retorna alguma resposta para método GET ou outro método não suportado
        return HttpResponse("Método não suportado", status=405)
