# minimot
<br>I love data and I love Youtube, so this is a passion project.

<br>run by cd'ing to the minimot directory and putting this command:
<br>python src/app.py

<br>This is a currently (very) wonky program that can:
<br>Count how many times a word or phrase appeared in a Youtuber's or Playlist's transcripts. (ana)
<br>Count the first words or words of any position, to find the most common ones. (first_ana)
<br>Visualize these counts.
<br>Download transcripts en masse. (dloader) 

The downloader application downloads video subtitles and video metadata from a channel or playlist of choice.
<br>It gets all metadata of the video, like view counts and duration
<br>It is the most wonkiest part of this application as it uses yt-dlp and constantly freezes during downloading.
<br>A way to circumvent the freezing is to close the entire program and run it again. 
<br>The program will save and track the already downloaded data so the program does not need to download it again.

<br>This data can be used in the analyzers. 

TODO: make a better downloader, do whatever to make it better due to the high importance of the tool!
<br>Like in batch cleaning and batch updating/downloading. 
<br>These batch processes should be implemented carefully. 
<br>Maybe use BOTH human programming and AI pair programming for debugging, due to the fact that one unseen error can mess up so much data. 
<br> > good practice for that, batch metadata is easy to implement w/o AI, it uses the same functions as regular downloading, but depreciated features.

<br>I want to improve on it after learning techniques in class. 

<br>For integrity, I did use AI pair programming for this project, especially for the programs with the ana suffix on it.
AI was used to debug but not organize the structure of the project. 
