import discord

intents = discord.Intents.default()
client = discord.Client(intents=intents)
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
bot_token = os.getenv('TOKEN')

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@discord.ext.command.command()
async def validate(ctx, u_input: str):
    '''Transforms user input into a comma separated list of beatmap ids'''
    map_ids = sanitize(u_input)

    await ctx.send('Foo!')


def sanitize(u_input: str) -> list[int]:
    ids = []

    # Split the input by commas, spaces, or tabs
    parts = u_input.replace(',', ' ').replace('\t', ' ').split()

    for part in parts:
        try:
            # Try to convert each part to an integer
            ids.append(int(part))
        except ValueError:
            # If any part is not an integer, return an empty list
            return []

    return ids

def oss_client() -> Ossapi:
    return Ossapi(client_id, client_secret)

def run():
    token = os.getenv('TOKEN')
    client.run(token)