const fetch = require('node-fetch');
async function test() {
  const req = await fetch('http://127.0.0.1:17842/api/provider/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target: 'weather', provider: 'default' })
  });
  console.log(await req.text());
}
test();
