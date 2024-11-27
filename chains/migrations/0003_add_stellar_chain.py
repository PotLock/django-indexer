from django.db import migrations


def create_stellar_chain(apps, schema_editor):
    Chain = apps.get_model("chains", "Chain")
    # Create the "stellar" chain
    stellar_chain, created = Chain.objects.get_or_create(
        name="stellar", defaults={"evm_compat": False}
    )

    # Set "stellar" chain as the default for all existing accounts
    Round = apps.get_model("grantpicks", "Round")
    Round.objects.update(chain=stellar_chain)
    print("Updated all Rounds to use stellar chain")


class Migration(migrations.Migration):

    dependencies = [("chains", "0001_initial"), ("chains", "0002_add_near_chain"),  ("grantpicks", "0001_initial"), ("grantpicks", "0002_round_chain_rounddeposit_memo_and_more")]

    operations = [
        migrations.RunPython(create_stellar_chain),
    ]
