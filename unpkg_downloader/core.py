import http
import dateutil.parser
import zipfile
import asyncio
import aiohttp
import click
import json

def get_list(url):
    print(url)
    conn = http.client.HTTPSConnection('unpkg.com')
    conn.request('GET', url[17:])
    resp = conn.getresponse()
    if resp.status != 200:
        url = resp.headers['location']
        conn.close()
        print(url)
        conn.request('GET', url)

    resp = conn.getresponse()
    r = resp.read()
    conn.close()

    return json.loads(r)


def get_all_url_from_json(json, url_times):
    if json['type'] == 'file':
        url_times.append([json['path'], json['lastModified']])
    else:
        for file in json['files']:
            url_times += get_all_url_from_json(file, [])
    return url_times


async def fetch(client, f_url):
    async with client.get(f_url) as resp:
        assert resp.status == 200
        return await resp.read()


async def task(loop, i, base_url, f_url, f_time, zf):
    ztime = dateutil.parser.parse(f_time).timetuple()[:6]
    zinfo = zipfile.ZipInfo(filename=f_url[1:], date_time=ztime)
    zinfo.compress_type=zipfile.ZIP_DEFLATED
    async with aiohttp.ClientSession(loop=loop) as client:
        context = await fetch(client, base_url + f_url)
        zf.writestr(zinfo, context)
        click.echo('%i %s' % (i+1, f_url))


def aio_get_all_url(url, zip_path):
    json = get_list(url)
    url_times = get_all_url_from_json(json, [])
    click.echo('total: %i' % len(url_times))

    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:

        tasks = [asyncio.ensure_future(
                     task(loop, i, url[:-5], f_url, f_time, zf))
                for i, (f_url, f_time) in enumerate(url_times)]
        loop.run_until_complete(asyncio.wait(tasks))
        
    loop.close()


@click.command()
@click.argument('name_version')
@click.argument('path', nargs=-1)
def cli(name_version, path):
    url = 'https://unpkg.com/{name_version}/?json'.format(name_version=name_version)
    if not path:
        path = '_'.join(name_version.split('@')) + '.zip'
    else:
        path = path[0]
    aio_get_all_url(url, path)


if __name__ == '__main__':
    cli()

