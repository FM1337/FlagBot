import discord
import io
import os
import textwrap
from contextlib import redirect_stdout
import traceback
from discord.ext import commands


# Borrowed from https://github.com/chenzw95/porygon/blob/master/cogs/debug.py with slight modifications
class PythonInterpreter(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])
        # remove `foo`
        return content.strip('` \n')

    # Executes/evaluates code.Pretty much the same as Rapptz implementation for RoboDanny with slight variations.
    async def interpreter(self, env, code, ctx):
        body = self.cleanup_code(code)
        stdout = io.StringIO()
        to_compile = 'async def func():\n{}'.format(textwrap.indent(body, "  "))
        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send('```\n{}: {}\n```'.format(e.__class__.__name__, e))
        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.message.add_reaction("❌")
            await ctx.send('```\n{}{}\n```'.format(value, traceback.format_exc()))
        else:
            await ctx.message.add_reaction("✅")
            value = stdout.getvalue()
            result = None
            if ret is None:
                if value:
                    result = '```\n{}\n```'.format(value)
                else:
                    try:
                        result = '```\n{}\n```'.format(repr(eval(body, env)))
                    except:
                        pass
            else:
                self._last_result = ret
                result = '```\n{}{}\n```'.format(value, ret)
            if result:
                log_msg = body.replace('`', r'\`')
                if not log_msg[0:3] == '```':
                    log_msg = '```' + log_msg + '```'
                await self.bot.interpreter_logs_channel.send("Interpreter used by {} in {}:\n{}".format(ctx.author, ctx.channel.mention, log_msg))
                if len(str(result)) > 1900:
                    await ctx.send("Large output:", file=discord.File(io.BytesIO(result.encode("utf-8")), filename="output.txt"))
                    await self.bot.interpreter_logs_channel.send("Large Result:", file=discord.File(io.BytesIO(result.encode("utf-8")), filename="output.txt"))
                    for user in (self.bot.creator, self.bot.allen, self.bot.pie):
                        await user.send("Large Result:", file=discord.File(io.BytesIO(result.encode("utf-8")), filename="output.txt"))
                else:
                    await ctx.send(result)
                    await self.bot.interpreter_logs_channel.send("Result: {}".format(result))
                    for user in (self.bot.creator, self.bot.allen, self.bot.pie):
                        await user.send("Result: {}".format(result))


    @commands.group(hidden=True)
    @commands.has_any_role("Bot Dev", "FlagBrew Team", "Discord Moderator")
    async def py(self, ctx, *, msg):
        """Python interpreter. Limited to bot devs, flagbrew team, and staff"""
        blocked_libraries_and_terms = [
            'requests',
            'aiohttp',
            '/etc',
            '/etc/shadow',
            '/etc/passwd',
            'passwd',
            'shadow',
            '/home',
            'home',
            'requests_futures',
            'sys',
            'raise'
        ]
        if any(b in msg for b in blocked_libraries_and_terms):
            return await ctx.send("Something in your code isn't allowed. Cancelling code execution.")
        log_msg = self.cleanup_code(msg).replace('`', r'\`')
        if not log_msg[0:3] == '```':
            log_msg = '```' + log_msg + '```'
        for user in (self.bot.creator, self.bot.allen, self.bot.pie):
            await user.send("Interpreter used by {} in {}:\n{}".format(ctx.author, ctx.channel.mention, log_msg))
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'server': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }
        env.update(globals())
        await self.interpreter(env, msg, ctx)

    @commands.command()
    async def togglepy(self, ctx):
        """Toggles the python interpreter. Bot creator and allen only"""
        if not ctx.author in (self.bot.creator, self.bot.allen):
            raise commands.errors.CheckFailure()
        pycmd = self.bot.get_command('py')
        if pycmd.enabled:
            pycmd.enabled = False
            return await ctx.send("Disabled the py command!")
        else:
            pycmd.enabled = True
            return await ctx.send("Enabled the py command!")


def setup(bot):
    bot.add_cog(PythonInterpreter(bot))