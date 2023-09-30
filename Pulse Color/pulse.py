import disnake
import webcolors
from disnake.ext import commands
from config import TOKEN
from disnake.errors import NotFound


intents = disnake.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

# Dictionary to store users who have changed their color
user_color_change = {}
# Dictionary to store the ceiling role for each guild
guild_ceiling_roles = {}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Bot is ready: {bot.user.name}")
    
    funny_status = "/help | Report any Issues to @daddylad"
    truncated_status = (funny_status[:46] + "...") if len(funny_status) > 49 else funny_status
    await bot.change_presence(activity=disnake.Activity(type=disnake.ActivityType.listening, name=truncated_status))

@bot.slash_command()
async def help(ctx):
    help_text = """
**/colorchange**: Change your role color to a specified color.
- Run: /colorchange 
- type color name when Bot prompts : Please type the color name or hex code you want for your role.
- Note: You can change your color only once.
"""

    await ctx.send(help_text, ephemeral=True)

# Generate a list of valid color names
valid_color_names = list(webcolors.CSS3_HEX_TO_NAMES.values())

@bot.slash_command()
async def setup(ctx, ceiling_role: disnake.Role):
    if ctx.author.guild_permissions.administrator:
        bot_member = ctx.guild.get_member(bot.user.id)
        if bot_member:
            bot_highest_role = sorted(bot_member.roles, key=lambda r: r.position, reverse=True)[0]
            if bot_highest_role.position > ceiling_role.position:
                guild_ceiling_roles[ctx.guild.id] = ceiling_role.id
                await ctx.send(f"Ceiling role set to {ceiling_role.name}.", ephemeral=True)
            else:
                await ctx.send("The bot's highest role must be higher than the ceiling role.", ephemeral=True)
        else:
            await ctx.send("Error: Bot member not found in the guild.", ephemeral=True)
    else:
        await ctx.send("You must be an admin to run this command.", ephemeral=True)


@bot.slash_command()
async def colorchange(ctx):
    user_id = ctx.author.id
    if user_id in user_color_change and user_color_change[user_id]:
        await ctx.send("You can only change your color once.", ephemeral=True)
        return

    await ctx.send("Please type the color name or hex code you want for your role.", ephemeral=True)
    color_message = await bot.wait_for('message', timeout=60.0, check=lambda message: message.author == ctx.author)

    try:
        await color_message.delete()
    except NotFound:
        pass
    

    color_input = color_message.content.lower().strip()
    role_name = None
    color = None

    if color_input in valid_color_names:
        role_name = f"{color_input.capitalize()}"
        rgb = webcolors.name_to_rgb(color_input)
        color = disnake.Color.from_rgb(*rgb)
    elif color_input.startswith("#"):
        try:
            role_name = f"{color_input.upper()}"
            rgb = webcolors.hex_to_rgb(color_input)
            color = disnake.Color.from_rgb(*rgb)
        except ValueError:
            await ctx.send("Invalid hex code. Please enter a valid one.", ephemeral=True)
            return

    if role_name:
        role_exists = disnake.utils.get(ctx.guild.roles, name=role_name)
        ceiling_role_id = guild_ceiling_roles.get(ctx.guild.id)
        ceiling_role = ctx.guild.get_role(ceiling_role_id) if ceiling_role_id else None
        position = ceiling_role.position - 1 if ceiling_role else 1

        if not role_exists:
            role = await ctx.guild.create_role(name=role_name, color=color)
            await role.edit(position=position)
            await ctx.send(f"Role {role_name} has been created.", ephemeral=True)
        else:
            role = role_exists

        await ctx.author.add_roles(role)
        await ctx.send(f"You have been added to the role {role_name}.", ephemeral=True)
        user_color_change[user_id] = True
    else:
        await ctx.send(f"Invalid color. Please enter a valid color name or hex code.", ephemeral=True)

@bot.slash_command(name="test_color")
async def test_color(ctx):
    user_id = ctx.author.id
    if user_id in user_color_change and user_color_change[user_id]:
        await ctx.send("You can only change your color once.", ephemeral=True)
        return

    await ctx.send("Please type the color name or hex code you want for your role.", ephemeral=True)
    color_message = await bot.wait_for('message', timeout=60.0, check=lambda message: message.author == ctx.author)

    try:
        await color_message.delete()
    except NotFound:
        pass

    color_input = color_message.content.lower().strip()
    role_name = None
    color = None

    if color_input in valid_color_names:
        role_name = f"{color_input.capitalize()}"
        rgb = webcolors.name_to_rgb(color_input)
        color = disnake.Color.from_rgb(*rgb)
    elif color_input.startswith("#"):
        try:
            role_name = f"{color_input.upper()}"
            rgb = webcolors.hex_to_rgb(color_input)
            color = disnake.Color.from_rgb(*rgb)
        except ValueError:
            await ctx.send("Invalid hex code. Please enter a valid one.", ephemeral=True)
            return

    if role_name:
        role_exists = disnake.utils.get(ctx.guild.roles, name=role_name)
        ceiling_role_id = guild_ceiling_roles.get(ctx.guild.id)
        ceiling_role = ctx.guild.get_role(ceiling_role_id) if ceiling_role_id else None
        position = ceiling_role.position - 1 if ceiling_role else 1

        if not role_exists:
            role = await ctx.guild.create_role(name=role_name, color=color)
            await role.edit(position=position)
            await ctx.send(f"Role {role_name} has been created.", ephemeral=True)
        else:
            role = role_exists

        await ctx.author.add_roles(role)
        await ctx.send(f"You have been added to the role {role_name}.", ephemeral=True)
        user_color_change[user_id] = True
    else:
        await ctx.send(f"Invalid color. Please enter a valid color name or hex code.", ephemeral=True)

@bot.slash_command()
async def reset(ctx, member: disnake.Member):
    if ctx.author.guild_permissions.administrator:
        if member.id in user_color_change:
            del user_color_change[member.id]
            await ctx.send(f"The color change limit for {member.display_name} has been reset.", ephemeral=True)
        else:
            await ctx.send(f"{member.display_name} has not changed their color yet.", ephemeral=True)
    else:
        await ctx.send("You must be an admin to run this command.", ephemeral=True)

bot.run(TOKEN)
