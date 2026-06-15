const https = require('https');

// Query Linear GraphQL API using API key
function fetchTasks(apiKey) {
  return new Promise((resolve, reject) => {
    const query = JSON.stringify({
      query: `
        query {
          issues(first: 20, orderBy: createdAt) {
            nodes {
              id
              identifier
              title
              state {
                name
              }
              priority
              priorityLabel
              assignee {
                name
                email
              }
              createdAt
              updatedAt
            }
          }
        }
      `
    });

    const options = {
      hostname: 'api.linear.app',
      path: '/graphql',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': apiKey,
        'Content-Length': Buffer.byteLength(query)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        if (res.statusCode === 200) {
          resolve(JSON.parse(data));
        } else {
          reject(new Error(`GraphQL query failed: ${res.statusCode} - ${data}`));
        }
      });
    });

    req.on('error', (e) => {
      reject(e);
    });

    req.write(query);
    req.end();
  });
}

// Main execution
async function main() {
  try {
    // Try using the client_id as API key first
    const apiKey = '';
    
    console.log('Fetching recent tasks from Linear...\n');
    const result = await fetchTasks(apiKey);
    
    if (result.errors) {
      console.error('GraphQL Errors:', JSON.stringify(result.errors, null, 2));
      console.error('\nNote: You may need a valid Linear API key. The provided credentials do not appear to be a valid API key.');
      console.error('Please obtain an API key from Linear Settings > API > Personal API keys');
      return;
    }

    const issues = result.data.issues.nodes;
    
    console.log(`=== Recent Tasks (${issues.length} found) ===\n`);
    
    issues.forEach((issue, index) => {
      console.log(`${index + 1}. [${issue.identifier}] ${issue.title}`);
      console.log(`   Status: ${issue.state.name}`);
      console.log(`   Priority: ${issue.priorityLabel || 'None'} (${issue.priority})`);
      console.log(`   Assignee: ${issue.assignee ? issue.assignee.name : 'Unassigned'}`);
      console.log(`   Created: ${new Date(issue.createdAt).toLocaleString()}`);
      console.log('');
    });

  } catch (error) {
    console.error('Error:', error.message);
    console.error('\nNote: The provided OAuth credentials do not appear to work with Linear API.');
    console.error('Linear typically requires a Personal API Key for authentication.');
    console.error('You can generate one at: https://linear.app/settings/api');
    process.exit(1);
  }
}

main();
