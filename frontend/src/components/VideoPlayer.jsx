// frontend/src/components/VideoPlayer.jsx
import { useRef, useEffect, useState } from 'react'

export default function VideoPlayer({
  videoUrl,
  currentTime,
  onTimeUpdate,
  onPlay,
  onPause,
  onSeek,
}) {
  const videoRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [volume, setVolume] = useState(1)
  const [playbackRate, setPlaybackRate] = useState(1)

  // Sync external currentTime changes (e.g., from transcript clicks)
  useEffect(() => {
    if (videoRef.current && currentTime !== undefined) {
      const diff = Math.abs(videoRef.current.currentTime - currentTime)
      // Only seek if difference is significant (avoid feedback loops)
      if (diff > 0.5) {
        videoRef.current.currentTime = currentTime
      }
    }
  }, [currentTime])

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      onTimeUpdate?.(videoRef.current.currentTime)
    }
  }

  const handlePlay = () => {
    setIsPlaying(true)
    onPlay?.()
  }

  const handlePause = () => {
    setIsPlaying(false)
    onPause?.()
  }

  const handleSeek = (time) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time
      onSeek?.(time)
    }
  }

  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
    }
  }

  const formatTime = (seconds) => {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="bg-slate-900 rounded-lg overflow-hidden flex flex-col h-full min-h-0">
      <div className="flex-1 flex items-center justify-center min-h-0 overflow-hidden">
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          onTimeUpdate={handleTimeUpdate}
          onPlay={handlePlay}
          onPause={handlePause}
          onLoadedMetadata={() => {
            if (videoRef.current) {
              setVolume(videoRef.current.volume)
            }
          }}
        />
      </div>

      {/* Controls */}
      <div className="bg-slate-800 p-4 space-y-3 flex-shrink-0">
        {/* Progress Bar */}
        <div className="flex items-center gap-2">
          <button
            onClick={togglePlayPause}
            className="text-white hover:text-yellow-400"
          >
            {isPlaying ? (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M5.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75A.75.75 0 007.25 3h-1.5zM12.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75a.75.75 0 00-.75-.75h-1.5z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
              </svg>
            )}
          </button>
          <span className="text-xs text-slate-300 font-mono">
            {formatTime(videoRef.current?.currentTime || 0)}
          </span>
          <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-yellow-500"
              style={{
                width: `${
                  videoRef.current
                    ? (videoRef.current.currentTime / videoRef.current.duration) * 100
                    : 0
                }%`,
              }}
            />
          </div>
          <span className="text-xs text-slate-300 font-mono">
            {formatTime(videoRef.current?.duration || 0)}
          </span>
        </div>

        {/* Speed and Volume Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const rates = [0.5, 0.75, 1, 1.25, 1.5, 2]
                const currentIndex = rates.indexOf(playbackRate)
                const nextRate = rates[(currentIndex + 1) % rates.length]
                setPlaybackRate(nextRate)
                if (videoRef.current) {
                  videoRef.current.playbackRate = nextRate
                }
              }}
              className="text-xs text-slate-300 hover:text-white"
            >
              {playbackRate}x Speed
            </button>
          </div>
          <div className="flex items-center gap-2">
            {/* <span className="text-xs text-slate-400">Source Volume</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={0}
              className="w-20"
            /> */}
            <span className="text-xs text-slate-400">Voiceover/Dub Volume</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={volume}
              onChange={(e) => {
                const vol = parseFloat(e.target.value)
                setVolume(vol)
                if (videoRef.current) {
                  videoRef.current.volume = vol
                }
              }}
              className="w-20"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

