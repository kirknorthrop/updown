from django.core.management import call_command

def main(args):
    call_command('update_incidents')