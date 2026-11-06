const { test, before, after, describe } = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const net = require('node:net');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const TOKEN = 'token-admin-usado-apenas-nos-testes';
const PLACEHOLDER = 'troque-por-um-token-admin-forte';
const REPORT = '/api/admin/financial-report';

const freePort = () => new Promise((resolve) => {
    const probe = net.createServer();
    probe.listen(0, '127.0.0.1', () => {
        const { port } = probe.address();
        probe.close(() => resolve(port));
    });
});

async function startServer(adminToken) {
    const port = await freePort();
    const child = spawn(process.execPath, ['src/app.js'], {
        cwd: ROOT,
        env: { ...process.env, PORT: String(port), DB_PATH: ':memory:', ADMIN_TOKEN: adminToken },
    });
    const server = { child, base: `http://127.0.0.1:${port}`, log: '' };
    child.stdout.on('data', (chunk) => { server.log += chunk; });
    child.stderr.on('data', (chunk) => { server.log += chunk; });

    for (let attempt = 0; attempt < 50; attempt += 1) {
        try {
            await fetch(server.base);
            return server;
        } catch {
            await new Promise((resolve) => setTimeout(resolve, 100));
        }
    }
    throw new Error(`Servidor não subiu: ${server.log}`);
}

const stopServer = (server) => new Promise((resolve) => {
    server.child.once('exit', resolve);
    server.child.kill();
});

const request = async (server, method, url, { body, token } = {}) => {
    const headers = { 'content-type': 'application/json' };
    if (token !== undefined) headers['x-admin-token'] = token;
    const response = await fetch(server.base + url, {
        method,
        headers,
        body: body === undefined ? undefined : typeof body === 'string' ? body : JSON.stringify(body),
    });
    return { status: response.status, text: await response.text() };
};

const checkout = (over = {}) => ({
    usr: 'Gui', eml: 'gui@x.com', pwd: 'senhaforte', c_id: 2, card: '4111222233334444', ...over,
});

describe('com ADMIN_TOKEN configurado', () => {
    let server;
    before(async () => { server = await startServer(TOKEN); });
    after(async () => { await stopServer(server); });

    test('contrato do checkout', async () => {
        const approved = await request(server, 'POST', '/api/checkout', { body: checkout() });
        assert.equal(approved.status, 200);
        assert.equal(approved.text, '{"msg":"Sucesso","enrollment_id":2}');

        const denied = await request(server, 'POST', '/api/checkout', { body: checkout({ eml: 'nega@x.com', card: '5111' }) });
        assert.deepEqual([denied.status, denied.text], [400, 'Pagamento recusado']);

        const missing = await request(server, 'POST', '/api/checkout', { body: {} });
        assert.deepEqual([missing.status, missing.text], [400, 'Bad Request']);

        const unknown = await request(server, 'POST', '/api/checkout', { body: checkout({ c_id: 99 }) });
        assert.deepEqual([unknown.status, unknown.text], [404, 'Curso não encontrado']);
    });

    test('e-mail existente exige a senha da conta', async () => {
        const owner = { eml: 'dona@x.com', pwd: 'senha-da-dona' };
        assert.equal((await request(server, 'POST', '/api/checkout', { body: checkout(owner) })).status, 200);
        assert.equal((await request(server, 'POST', '/api/checkout', { body: checkout({ ...owner, c_id: 1 }) })).status, 200);
        assert.equal((await request(server, 'POST', '/api/checkout', { body: checkout({ ...owner, pwd: 'errada' }) })).status, 401);
        assert.equal((await request(server, 'POST', '/api/checkout', { body: checkout({ eml: owner.eml, pwd: undefined }) })).status, 401);
    });

    test('checkout sem pwd cria conta com senha aleatória', async () => {
        assert.equal((await request(server, 'POST', '/api/checkout', { body: checkout({ eml: 'sem@x.com', pwd: undefined }) })).status, 200);
    });

    test('senhas antigas não abrem a conta do seed', async () => {
        for (const pwd of ['123', '123456', 'change-me-seed']) {
            const response = await request(server, 'POST', '/api/checkout', { body: checkout({ eml: 'leonan@fullcycle.com.br', pwd }) });
            assert.equal(response.status, 401, pwd);
        }
    });

    test('entradas que derrubavam o original recebem 400 e o processo continua vivo', async () => {
        const invalid = [
            { card: 123 }, { eml: 'n@x.com', pwd: 123 }, { eml: 'x' }, { c_id: 'abc' }, { c_id: true }, { c_id: -1 },
        ];
        for (const over of invalid) {
            const response = await request(server, 'POST', '/api/checkout', { body: checkout(over) });
            assert.equal(response.status, 400, JSON.stringify(over));
        }
        assert.equal((await request(server, 'POST', '/api/checkout', { body: '[]' })).status, 400);
        assert.equal((await request(server, 'POST', '/api/checkout', { body: '{oops' })).status, 400);
        assert.equal((await request(server, 'DELETE', '/api/users/abc', { token: TOKEN })).status, 400);
        assert.equal(server.child.exitCode, null);
    });

    test('rotas admin negam sem credencial válida', async () => {
        for (const [method, url] of [['GET', REPORT], ['DELETE', '/api/users/1']]) {
            assert.equal((await request(server, method, url)).status, 401);
            assert.equal((await request(server, method, url, { token: 'errado' })).status, 401);
            assert.equal((await request(server, method, url, { token: PLACEHOLDER })).status, 401);
        }
    });

    test('relatório em ordem estável e DELETE sem órfãos', async () => {
        const before = await request(server, 'GET', REPORT, { token: TOKEN });
        assert.equal(before.status, 200);
        assert.equal(JSON.parse(before.text)[0].course, 'Clean Architecture');

        const removed = await request(server, 'DELETE', '/api/users/1', { token: TOKEN });
        assert.equal(removed.status, 200);

        const report = await request(server, 'GET', REPORT, { token: TOKEN });
        assert.ok(!report.text.includes('Unknown'));
    });

    test('log não traz cartão completo, chave nem senha', () => {
        for (const secret of ['4111222233334444', 'pk_live_', 'senhaforte', TOKEN]) {
            assert.ok(!server.log.includes(secret), secret);
        }
    });
});

for (const [name, adminToken] of [['sem ADMIN_TOKEN', ''], ['com o placeholder do .env.example', PLACEHOLDER]]) {
    describe(name, () => {
        let server;
        before(async () => { server = await startServer(adminToken); });
        after(async () => { await stopServer(server); });

        test('rotas admin respondem 403', async () => {
            for (const [method, url] of [['GET', REPORT], ['DELETE', '/api/users/1']]) {
                assert.equal((await request(server, method, url)).status, 403);
                assert.equal((await request(server, method, url, { token: PLACEHOLDER })).status, 403);
            }
        });
    });
}
