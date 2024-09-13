require('dotenv').config();
const express = require('express');
const multer = require('multer');
const Redis = require('ioredis');
const { v4: uuidv4 } = require('uuid');

const app = express();
const upload = multer({ dest: 'uploads/' });
const redis = new Redis();

app.use(express.static('public'));
app.use(express.json());

app.post('/scan', upload.array('menus'), async (req, res) => {
  console.log('Received scan request');
  const jobId = uuidv4();
  const job = {
    id: jobId,
    files: req.files.map(file => file.path)
  };
  
  console.log(`Creating job ${jobId} with files:`, job.files);
  try {
    await redis.lpush('menu_queue', JSON.stringify(job));
    console.log(`Job ${jobId} added to queue`);
    res.json({ jobId });
  } catch (error) {
    console.error(`Error adding job ${jobId} to queue:`, error);
    res.status(500).json({ error: 'Failed to process request' });
  }
});

app.get('/status/:jobId', async (req, res) => {
  try {
    const status = await redis.get(`status:${req.params.jobId}`);
    console.log(`Status for job ${req.params.jobId}:`, status);
    res.json({ status: status || 'processing' });
  } catch (error) {
    console.error(`Error getting status for job ${req.params.jobId}:`, error);
    res.status(500).json({ error: 'Failed to get job status' });
  }
});

app.get('/questions/:jobId', async (req, res) => {
  try {
    console.log(`Received request for questions for job ${req.params.jobId}`);
    const questions = await redis.get(`questions:${req.params.jobId}`);
    console.log(`Retrieved questions from Redis for job ${req.params.jobId}:`, questions);
    
    if (questions) {
      res.json(JSON.parse(questions));
    } else {
      res.status(404).json({ error: 'Questions not found' });
    }
  } catch (error) {
    console.error(`Error retrieving questions for job ${req.params.jobId}:`, error);
    res.status(500).json({ error: 'Failed to get questions' });
  }
});

app.post('/preferences/:jobId', async (req, res) => {
  try {
    const jobId = req.params.jobId;
    const { preferences } = req.body;
    
    // Check if preferences have already been submitted
    const existingPreferences = await redis.get(`user_preferences:${jobId}`);
    if (existingPreferences) {
      console.log(`Preferences already exist for job ${jobId}. Ignoring duplicate submission.`);
      return res.status(409).json({ message: 'Preferences already submitted' });
    }

    // Save preferences
    await redis.set(`user_preferences:${jobId}`, JSON.stringify(preferences));
    console.log(`Preferences saved for job ${jobId}`);

    // Update job status
    await redis.set(`status:${jobId}`, 'preferences_received');
    
    res.json({ message: 'Preferences received' });
  } catch (error) {
    console.error(`Error saving preferences for job ${req.params.jobId}:`, error);
    res.status(500).json({ error: 'Failed to save preferences' });
  }
});

app.get('/result/:jobId', async (req, res) => {
  try {
    console.log(`Checking result for job ${req.params.jobId}`);
    const result = await redis.get(`result:${req.params.jobId}`);
    console.log(`Result for job ${req.params.jobId}:`, result);
    
    if (result) {
      res.json(JSON.parse(result));
    } else {
      res.status(404).json({ error: 'Result not found' });
    }
  } catch (error) {
    console.error(`Error retrieving result for job ${req.params.jobId}:`, error);
    res.status(500).json({ error: 'Failed to get result' });
  }
});

app.listen(3000, () => console.log('Server running on port 3000'));