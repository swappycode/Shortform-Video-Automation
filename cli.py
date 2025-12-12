import sys
a = sys.argv[1] if len(sys.argv) > 1 else "gui"
if a == "gui":
    from gui import main as _g
    _g()
elif a == "run":
    import main as m
    m.main()
elif a == "download":
    import download_models as dm
    dm.main()
elif a == "downloader":
    import downloader as d
    d.main()
else:
    print("usage: cli.py [gui|run|download|downloader]")
