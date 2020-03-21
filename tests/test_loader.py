from pathlib import Path
from miyadaiku import ContentSrc, loader


def test_walk_directory(sitedir):
    dir1 = (sitedir / 'dir1')
    dir1.mkdir()

    dir2 = dir1 / 'dir2'
    dir2.mkdir()

    file1 = (dir1 / 'file1')
    file1.write_text('')

    file11 = (dir1 / 'file1.props.yml')
    file11.write_text('name: value')


    file2 = (dir2 / 'file2')
    file2.write_text('')

    (dir1 / 'test.bak').write_text('')

    results = loader.walk_directory(sitedir, set(["*.bak"]))
    all = sorted(results, key=lambda d:d.srcpath)
    assert len(all) == 2

    assert all[0] == ContentSrc(srcpath=str(file2), contentpath=(('dir1', 'dir2',), 'file2'), package='', metadata={})
    assert all[1] == ContentSrc(srcpath=str(file1), contentpath=(('dir1',), 'file1'), package='', metadata={'name': 'value'})


def test_walkpackage(sitedir):
    results = loader.walk_package('package1', 'contents', set(["*.bak"]))
    all = sorted(results, key=lambda d:d.srcpath)
    
    assert len(all) == 7
    assert all[0] == ContentSrc(package='package1', srcpath='contents/dir1/a', contentpath=(('dir1',), 'a'), metadata={'test': 'value'})

