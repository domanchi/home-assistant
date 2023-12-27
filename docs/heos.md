# heos

## Problem

We want to play music on the HEOS-supported player through the homeassistant.
Furthermore, the following features should be supported:

-   Physically pressing the power button on the player should halt music.

## Implementation

The HEOS player is connected to a NAS, with selected music saved on disk. The
user configures the HEOS playlist via the HEOS app, and saves it as a custom
HEOS playlist.

The HomeAssistant is configured to integrate with the HEOS system via
https://www.home-assistant.io/integrations/heos. On the designated trigger, it
sends a command via the HEOS integration to play the specified playlist via
playlist name.

Playlist modifications are managed through the HEOS application.

## Alternatives Attempted

### MusicAssistant

I had high hopes for this integration, as it had direct Soundcloud support, and
offered a consistent interface for managing playlists for all vendors for smart
speakers.

However, its method of managing playlists was flawed. Specifically, it determined
when a song was over by reading the underlying player state. When the player
became "idle", it would start the next song in the playlist. Unfortunately, the
player made no distinction between having finished playing a song, and having
the system be turned off. Consequently, it created a bizarre user experience:
when the user was physically present in the room, and did not want music anymore,
they would turn off the player, only to have it turn on again with a different
song.

It was due to this that I had to find a native solution for the use case I was
solving for.

### Direct References

I do not know of any method to specify the direct NAS path to the desired playlist
via the HomeAssistant HEOS integration. Consequently, we need to create and manage
the custom playlist in HEOS, then refer to this custom playlist by name via the
integration configuration.

