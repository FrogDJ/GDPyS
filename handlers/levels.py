import logging
import aiohttp
from helpers.levelhelper import level_helper
from helpers.searchhelper import search_helper
from helpers.generalhelper import create_offsets_from_page, string_bool, joint_string, list_comma_string
from helpers.songhelper import songs
from helpers.userhelper import user_helper
from helpers.crypthelper import cipher_xor
from objects.levels import SearchQuery, Level
from constants import XorKeys, ResponseCodes

async def level_search_modular_hanlder(request : aiohttp.web.Request) -> aiohttp.web.Response:
    """Handles the get levels endpoint."""
    post_data = await  request.post()

    offset = create_offsets_from_page(int(post_data["page"]))
    logging.debug(offset)
    # Okay so here we have to create the search query object. May have to redo it but this should be sufficient for the time being.
    query = SearchQuery(
        int(post_data["type"]),
        offset,
        None, # Uncertain if order is used.
        int(post_data.get("gauntlet", 0)),
        string_bool(post_data.get("featured", "0")),
        string_bool(post_data.get("original", "0")),
        string_bool(post_data.get("epic", "0")),
        string_bool(post_data.get("twoPlayer", "0")),
        string_bool(post_data.get("star", "0")),
        string_bool(post_data.get("noStar", "0")),
        post_data.get("len", ""),
        int(post_data.get("song", 0)),
        int(post_data.get("customSong", 0)),
        post_data.get("diff", ""),
        post_data.get("str", "")
    )
    logging.debug(query)

    levels = await search_helper.get_levels(query)

    # Getting final reponse
    response = ""
    lvls_list = []
    song_str = ""
    user_str = ""
    gauntlet_append = "" if not query.gauntlet else f"44:{query.gauntlet}:"
    for level in levels.results:
        level : Level
        response += gauntlet_append
        lvls_list.append(level.ID)
        user_str += await user_helper.get_user_string(level.user_id) + "|"
        if level.song_id:
            song_str += songs.song_string(await songs.get_song_obj(level.song_id)) + "~:~"
        #THIS IS WHERE THE **FUN** BEGINS
        response += joint_string(
            {
                1 : level.ID,
                2 : level.name,
                5 : level.version,
                6 : level.user_id,
                8: 10,
                9 : level_helper.star_to_difficulty(level.stars),
                10 : level.downloads,
                12 : level.track,
                13 : level.game_version,
                14 : level.likes,
                17 : 1 if level.stars == 10 else 0,
                25 : 1 if level.stars == 1 else 0,
                18 : level.stars,
                19 : int(level.featured),
                42 : int(level.epic),
                45 : level.objects,
                3 : level.description,
                15 : level.length,
                30 : int(level.original),
                31 : 0,
                37 : level.coins,
                38 : int(level.verified_coins),
                39 : level.requested_stars,
                #41 : 1,
                47 : 2,
                40 : int(level.ldm),
                35 : level.song_id
            }
        ) + "|"
    
    response = response[:-1] + "#" + user_str[:-1] + "#" + song_str[:-3] + f"#{levels.total_results}:{offset}:10#" + await level_helper.multi_gen(lvls_list)
    logging.debug(response)
    return aiohttp.web.Response(text=response)

async def download_level(request : aiohttp.web.Request) -> aiohttp.web.Response:
    """Responsivle for downloading levels"""
    post_data = await request.post()

    level_id = int(post_data["levelID"])
    level = await level_helper.get_level_obj(level_id)
    if level is None:
        return aiohttp.web.Response(text=ResponseCodes.generic_fail)
    # Bump dl 
    await level_helper.bump_download(level_id)

    # Creating variables to be used.
    password_xor = cipher_xor(level.password, XorKeys.level_password)
    response = joint_string({
        1 : level.ID,
        2 : level.name,
        3 : level.description,
        4 : level.load_string(),
        5 : level.version,
        8 : 10,
        9 : level_helper.star_to_difficulty(level.stars),
        10 : level.downloads,
        11 : 1,
        12 : level.track,
        13 : level.game_version,
        14 : level.likes,
        17 : 1 if level.stars == 10 else 0,
        43 : level.demon_diff,
        25 : 1 if level.stars == 1 else 0,
        18 : level.stars,
        19 : int(level.featured),
        42 : int(level.epic),
        45 : level.objects,
        15 : level.length,
        30 : int(level.original),
        31 : 1,
        28 : level.upload_timestamp,
        29 : level.update_timestamp,
        35 : level.song_id,
        36 : level.extra,
        37 : level.coins,
        38 : int(level.verified_coins),
        39 : level.requested_stars,
        46 : 1,
        47 : 2,
        48 : 1,
        40 : int(level.ldm),
        27 : password_xor
    }) + f"#{level_helper.solo_gen(level.load_string())}#" + level_helper.solo_gen2(list_comma_string([
        level.user_id, level.stars, 1 if level.stars == 10 else 0, level.ID, int(level.verified_coins), int(level.featured), level.password, 0 # Featured ID
    ]))

    logging.debug(response)
    return aiohttp.web.Response(text=response)