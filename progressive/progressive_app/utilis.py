from django.template.loader import get_template
from django.http import HttpResponse
from weasyprint import HTML
import tempfile

def render_to_pdf(template_src, context_dict={}):
    """
    Renders a Django template to PDF using WeasyPrint.
    """
    template = get_template(template_src)
    html_string = template.render(context_dict)

    # Create a temporary file for PDF
    with tempfile.NamedTemporaryFile(delete=True) as output:
        HTML(string=html_string).write_pdf(output.name)
        output.seek(0)
        pdf = output.read()

    return pdf