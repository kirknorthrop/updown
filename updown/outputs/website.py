from mako.template import Template

from updown import settings, utils


def generate(problems, resolved, information, last_updated):
    # Then create the HTML file.
    udl_template = Template(filename=settings.TEMPLATE_FILE_LOCATION + 'index.tmpl')
    rendered_page = udl_template.render(
        problems=problems,
        problems_sort=sorted(problems),
        resolved=resolved,
        resolved_sort=sorted(resolved),
        information=information,
        information_sort=sorted(information),
        last_updated=last_updated.strftime('%H:%M %d %b'),
        production=settings.PRODUCTION
    )

    with open(settings.OUTPUT_FILE_LOCATION + 'index.html', 'w') as f:
        if isinstance(rendered_page, bytes):
            rendered_page = rendered_page.decode('utf-8')
        f.write(rendered_page)
