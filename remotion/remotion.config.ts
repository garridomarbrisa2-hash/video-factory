import {Config} from '@remotion/cli/config';

// GPU rasterization via DirectX on NVIDIA
Config.setChromiumOpenGlRenderer('angle');

// Concurrency — will be tuned by benchmark
Config.setConcurrency(8);

// NVENC encoding
Config.setHardwareAcceleration('if-possible');
Config.setVideoBitrate('8M');

// Bundle caching
Config.setCachingEnabled(true);
