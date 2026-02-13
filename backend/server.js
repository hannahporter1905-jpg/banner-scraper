const express = require('express');
const cors = require('cors');
const axios = require('axios');
const cheerio = require('cheerio');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Banner detection logic
function isBannerImage(img, $) {
  const width = parseInt(img.attr('width')) || 0;
  const height = parseInt(img.attr('height')) || 0;
  const src = img.attr('src') || '';
  
  // Check aspect ratio (wide images)
  const aspectRatio = width / height;
  
  // Check parent elements for banner-related classes/IDs
  const parent = img.parent();
  const parentClass = parent.attr('class') || '';
  const parentId = parent.attr('id') || '';
  const bannerKeywords = ['banner', 'hero', 'slider', 'carousel', 'header'];
  
  const hasBannerKeyword = bannerKeywords.some(keyword => 
    parentClass.toLowerCase().includes(keyword) || 
    parentId.toLowerCase().includes(keyword) ||
    src.toLowerCase().includes(keyword)
  );
  
  // Banner criteria
  return (
    (aspectRatio > 2 && width > 600) || // Wide aspect ratio
    hasBannerKeyword || // Banner-related elements
    width > 1000 // Large width
  );
}

app.post('/api/scrape', async (req, res) => {
  const { url } = req.body;
  
  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }
  
  try {
    // Validate URL
    new URL(url);
    
    // Fetch the webpage
    const response = await axios.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      },
      timeout: 10000
    });
    
    const html = response.data;
    const $ = cheerio.load(html);
    const banners = [];
    
    // Find all images
    $('img').each((i, elem) => {
      const img = $(elem);
      
      if (isBannerImage(img, $)) {
        let src = img.attr('src');
        
        // Handle relative URLs
        if (src && !src.startsWith('http')) {
          const baseUrl = new URL(url);
          src = new URL(src, baseUrl.origin).href;
        }
        
        banners.push({
          src: src,
          alt: img.attr('alt') || 'Banner image',
          width: img.attr('width') || 'auto',
          height: img.attr('height') || 'auto',
          type: 'Banner Image'
        });
      }
    });
    
    // Check for CSS background images
    $('[style*="background-image"]').each((i, elem) => {
      const style = $(elem).attr('style');
      const urlMatch = style.match(/url\(['"]?([^'")]+)['"]?\)/);
      
      if (urlMatch) {
        let src = urlMatch[1];
        
        if (!src.startsWith('http')) {
          const baseUrl = new URL(url);
          src = new URL(src, baseUrl.origin).href;
        }
        
        banners.push({
          src: src,
          alt: 'Background banner',
          width: 'auto',
          height: 'auto',
          type: 'Background Banner'
        });
      }
    });
    
    res.json({ 
      success: true, 
      count: banners.length,
      banners: banners 
    });
    
  } catch (error) {
    console.error('Scraping error:', error.message);
    res.status(500).json({ 
      error: 'Failed to scrape website',
      message: error.message 
    });
  }
});

app.get('/', (req, res) => {
  res.json({ message: 'Banner Scraper API is running' });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});