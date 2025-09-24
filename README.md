# minimot

<br>I love data and I love Youtube, so this is a passion project.

<br>run by cd'ing to the minimot directory and putting this command:
<br>python src/app.py

<br>This is a currently wonky program that can:
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

<br>I want to improve on it after learning techniques in class. 
<br>Maybe add an ML-like funcitonality where the program can predict what Youtuber a transcript is from after seeing two different bags of words and their counts from two different Youtubers.
<br>Maybe add a sentiment analysis function.

<br>For integrity, I did use AI pair programming for this project, especially for the programs with the ana suffix on it.
I learned from this that "vibe coding" truly does not work and one needs to understand the program to code with AI tools.
