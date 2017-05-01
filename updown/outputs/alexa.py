import json

from updown import settings, utils


def generate(problems, resolved, information, last_updated):

    if len(problems) == 0:
        alexa_string = 'There are currently no reported step free access issues on the \
            Transport for London network.'
    else:
        alexa_string = 'There are step free access issues at: '
        alexa_string += ', '.join(problems.keys()[0:-1])
        if len(problems) > 1:
            alexa_string += ' and '
        alexa_string += problems.keys()[-1]

    with open(settings.OUTPUT_FILE_LOCATION + 'problems.txt', 'w') as f:
        f.write(alexa_string)

    with open(settings.OUTPUT_FILE_LOCATION + 'problems.json', 'w') as f:
        alexa_json = {k.lower(): v['text'] for k, v in problems.items() + information.items()}

        f.write(json.dumps(alexa_json))
