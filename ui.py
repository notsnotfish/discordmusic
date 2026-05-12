import discord
import logging
import asyncio

from subsonic import Song, Album, Playlist, get_album_art_file

logger = logging.getLogger(__name__)



class SysMsg:
    ''' A class for sending system messages '''

    @staticmethod
    async def msg(interaction: discord.Interaction, header: str, message: str=None, thumbnail: str=None, *, ephemeral: bool=False) -> None:
        ''' Generic message function. Creates a message formatted as an embed '''

        # Check if interaction is still valid
        if interaction is None or interaction.guild is None:
            logger.warning("Cannot send message: interaction is no longer valid")
            return

        # Handle message over character limit
        if message is not None and len(message) > 4096:
            message = message[:4093] + "..."

        embed = discord.Embed(color=discord.Color(0x50C470), title=header, description=message)
        file = discord.utils.MISSING

        # Attach a thumbnail if one was provided (as a local file)
        if thumbnail is not None:
            try:
                file = discord.File(thumbnail, filename="image.png")
                embed.set_thumbnail(url="attachment://image.png")
            except Exception as e:
                logger.error(f"Failed to attach thumbnail: {e}")
                # Continue without the thumbnail

        # Attempt to send the message, up to 3 times
        attempt = 0
        while attempt < 3:
            try:
                # Check if the interaction response is already done
                if interaction.response.is_done():
                    # Use followup
                    await interaction.followup.send(file=file, embed=embed, ephemeral=ephemeral)
                    return
                else:
                    # Use initial response
                    await interaction.response.send_message(file=file, embed=embed, ephemeral=ephemeral)
                    return
            except discord.NotFound:
                logger.warning("Attempt %d at sending a system message failed (NotFound)...", attempt+1)
                attempt += 1
                # Short delay before retrying
                await asyncio.sleep(0.5)
            except discord.HTTPException as e:
                logger.warning("Attempt %d at sending a system message failed (HTTPException: %s)...", attempt+1, e)
                attempt += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error("Unexpected error when sending system message: %s", e)
                attempt += 1
                await asyncio.sleep(0.5)
        
        # If we've exhausted all attempts, log a more detailed error
        logger.error("Failed to send system message after %d attempts. Header: %s", attempt, header)


    @staticmethod
    async def now_playing(interaction: discord.Interaction, song: Song) -> None:
        ''' Sends a message containing the currently playing song '''
        cover_art = await get_album_art_file(song.cover_id)
        desc = f"**{song.title}** - *{song.artist}*\n{song.album} ({song.duration_printable})"
        await __class__.msg(interaction, "Now Playing:", desc, cover_art)

    @staticmethod
    async def playback_ended(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating playback has ended '''
        await __class__.msg(interaction, "Playback ended")

    @staticmethod
    async def disconnected(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating the bot disconnected from voice channel '''
        await __class__.msg(interaction, "Disconnected from voice channel")

    @staticmethod
    async def starting_queue_playback(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating queue playback has started '''
        await __class__.msg(interaction, "Started queue playback")

    @staticmethod
    async def stopping_queue_playback(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating queue playback has stopped '''
        await __class__.msg(interaction, "Stopped queue playback")

    @staticmethod
    async def added_to_queue(interaction: discord.Interaction, song: Song) -> None:
        ''' Sends a message indicating the selected song was added to queue '''
        desc = f"**{song.title}** - *{song.artist}*\n{song.album} ({song.duration_printable})"
        cover_art = await get_album_art_file(song.cover_id)
        await __class__.msg(interaction, f"{interaction.user.display_name} added track to queue", desc, cover_art)

    @staticmethod
    async def added_album_to_queue(interaction: discord.Interaction, album: Album) -> None:
        ''' Sends a message indicating the selected album was added to queue '''
        desc = f"**{album.name}** - *{album.artist}*\n{album.song_count} songs ({album.duration} seconds)"
        cover_art = await get_album_art_file(album.cover_id)
        await __class__.msg(interaction, f"{interaction.user.display_name} added album to queue", desc, cover_art)

    @staticmethod
    async def added_playlist_to_queue(interaction: discord.Interaction, playlist: Playlist) -> None:
        ''' Sends a message indicating the selected playlist was added to queue '''
        desc = f"**{playlist.name}**\n{playlist.song_count} songs ({playlist.duration} seconds)"
        cover_art = await get_album_art_file(playlist.cover_id)
        await __class__.msg(interaction, f"{interaction.user.display_name} added playlist to queue", desc, cover_art)

    @staticmethod
    async def added_discography_to_queue(interaction: discord.Interaction, artist: str, albums: list[Album]) -> None:
        ''' Sends a message indicating the selected artist's discography was added to queue '''
        desc = f"**{artist}**\n{len(albums)} albums\n\n"
        cover_art = await get_album_art_file(albums[0].cover_id)
        for counter in range(len(albums)):
            album = albums[counter]
            desc += f"**{str(counter+1)}. {album.name}**\n{album.song_count} songs ({album.duration} seconds)\n\n" 
        await __class__.msg(interaction, f"{interaction.user.display_name} added discography to queue", desc, cover_art)

    @staticmethod
    async def queue_cleared(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating a user cleared the queue '''
        await __class__.msg(interaction, f"{interaction.user.display_name} cleared the queue")

    @staticmethod
    async def skipping(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating the current song was skipped '''
        await __class__.msg(interaction, "Skipped track", ephemeral=True)


class ErrMsg:
    ''' A class for sending error messages '''

    @staticmethod
    async def msg(interaction: discord.Interaction, message: str) -> None:
        ''' Generic message function. Creates an error message formatted as an embed '''
        
        # Check if interaction is still valid
        if interaction is None or interaction.guild is None:
            logger.warning("Cannot send error message: interaction is no longer valid")
            return
            
        embed = discord.Embed(color=discord.Color(0x50C470), title="Error", description=message)

        # Attempt to send the error message, up to 3 times
        attempt = 0
        while attempt < 3:
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
            except discord.NotFound:
                logger.warning("Attempt %d at sending an error message failed (NotFound)...", attempt+1)
                attempt += 1
                # Short delay before retrying
                await asyncio.sleep(0.5)
            except discord.HTTPException as e:
                logger.warning("Attempt %d at sending an error message failed (HTTPException: %s)...", attempt+1, e)
                attempt += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error("Unexpected error when sending error message: %s", e)
                attempt += 1
                await asyncio.sleep(0.5)
        
        # If we've exhausted all attempts, log a more detailed error
        logger.error("Failed to send error message after %d attempts. Message: %s", attempt, message)

    @staticmethod
    async def user_not_in_voice_channel(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating user is not in a voice channel '''
        await __class__.msg(interaction, "You are not connected to a voice channel.")

    @staticmethod
    async def bot_not_in_voice_channel(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating bot is connect to a voice channel '''
        await __class__.msg(interaction, "Not currently connected to a voice channel.")

    @staticmethod
    async def cannot_connect_to_voice_channel(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating bot is unable to connect to a voice channel '''
        await __class__.msg(interaction, "Cannot connect to voice channel.")

    @staticmethod
    async def queue_is_empty(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating the queue is empty '''
        await __class__.msg(interaction, "Queue is empty.")

    @staticmethod
    async def already_playing(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating that music is already playing '''
        await __class__.msg(interaction, "Already playing.")

    @staticmethod
    async def not_playing(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating nothing is playing '''
        await __class__.msg(interaction, "No track is playing.")



# Methods for parsing data to Discord structures
def parse_search_as_track_selection_embed(results: list[Song], query: str, page_num: int) -> discord.Embed:
    ''' Takes search results obtained from the Subsonic API and parses them into a Discord embed suitable for track selection '''

    options_str = ""

    # Loop over the provided search results
    for song in results:

        # Trim displayed tags to fit neatly within the embed
        tr_title = song.title
        tr_artist = song.artist
        tr_album = (song.album[:68] + "...") if len(song.album) > 68 else song.album

        # Only trim the longest tag on the first line
        top_str_length = len(song.title + " - " + song.artist)
        if top_str_length > 71:
            
            if tr_title > tr_artist:
                tr_title = song.title[:(68 - top_str_length)] + '...'
            else:
                tr_artist = song.artist[:(68 - top_str_length)] + '...'

        # Add each of the results to our output string
        options_str += f"**{tr_title}** - *{tr_artist}* \n*{tr_album}* ({song.duration_printable})\n\n"

    # Add the current page number to our results
    options_str += f"Current page: {page_num}"

    # Return an embed that displays our output string
    return discord.Embed(color=discord.Color.orange(), title=f"Results for: {query}", description=options_str)


def parse_search_as_track_selection_options(results: list[Song]) -> list[discord.SelectOption]:
    ''' Takes search results obtained from the Subsonic API and parses them into a Discord selection list for tracks '''

    select_options = []
    for i, song in enumerate(results):
        select_option = discord.SelectOption(label=f"{song.title}", description=f"by {song.artist}", value=i)
        select_options.append(select_option)

    return select_options
