from __future__ import print_function
from __future__ import absolute_import
from webassets.six import StringIO
from contextlib import contextmanager
from webassets.filter import Filter

try:
    from spritecss.main import CSSFile
    from spritecss.css import CSSParser
    from spritecss.css.parser import iter_print_css
    from spritecss.config import CSSConfig
    from spritecss.mapper import SpriteMapCollector
    from spritecss.packing import PackedBoxes, print_packed_size
    from spritecss.packing.sprites import open_sprites
    from spritecss.stitch import stitch
    from spritecss.replacer import SpriteReplacer

except ImportError:
    spritecss_loaded = False

else:
    spritecss_loaded = True

    class FakeCSSFile(CSSFile):
        """
        A custom subclass of spritecss.main.CSSFile that accepts CSS input
        as string data, instead of requiring that a CSS file be read from
        disk.
        """

        def __init__(self, fname, conf=None, data=''):
            super(FakeCSSFile, self).__init__(fname, conf=conf)
            self.data = StringIO(data)

        @contextmanager
        def open_parser(self):
            yield CSSParser.read_file(self.data)


__all__ = ('Spritemapper',)


class Spritemapper(Filter):
    """
    Generate CSS spritemaps using
    `Spritemapper <http://yostudios.github.com/Spritemapper/>`_, a Python
    utility that merges multiple images into one and generates CSS positioning
    for the corresponding slices. Installation is easy::

        pip install spritemapper

    Supported configuration options:

    SPRITEMAPPER_PADDING
        A tuple of integers indicating the number of pixels of padding to
        place between sprites

    SPRITEMAPPER_ANNEAL_STEPS
        Affects the number of combinations to be attempted by the box packer
        algorithm

    **Note:** Since the ``spritemapper`` command-line utility expects source
    and output files to be on the filesystem, this filter interfaces directly
    with library internals instead. It has been tested to work with
    Spritemapper version 1.0.
    """

    name = 'spritemapper'

    def setup(self):

        if not spritecss_loaded:
            raise EnvironmentError(
                "The spritemapper package could not be found."
            )

        self.options = {}
        padding = self.get_config('SPRITEMAPPER_PADDING', require=False)
        if padding:
            self.options['padding'] = padding
        anneal_steps = self.get_config('SPRITEMAPPER_ANNEAL_STEPS', require=False)
        if anneal_steps:
            self.options['anneal_steps'] = anneal_steps

    def input(self, _in, out, **kw):

        source_path = kw['source_path']

        # Save the input data for later
        css = _in.read()

        # Build config object
        conf = CSSConfig(base=self.options, fname=source_path)

        # Instantiate a dummy file instance
        cssfile = FakeCSSFile(fname=source_path, conf=conf, data=css)

        # Find spritemaps
        smaps = SpriteMapCollector(conf=conf)
        smaps.collect(cssfile.map_sprites())

        # Weed out single-image spritemaps
        smaps = [sm for sm in smaps if len(sm) > 1]

        # Generate spritemapped image
        # This code is almost verbatim from spritecss.main.spritemap
        sm_plcs = []
        for smap in smaps:
            with open_sprites(smap, pad=conf.padding) as sprites:
                print(("Packing sprites in mapping %s" % (smap.fname,)))
                packed = PackedBoxes(sprites, anneal_steps=conf.anneal_steps)
                print_packed_size(packed)
                sm_plcs.append((smap, packed.placements))
                print(("Writing spritemap image at %s" % (smap.fname,)))
                im = stitch(packed)
                with open(smap.fname, "wb") as fp:
                    im.save(fp)

        # Instantiate a fake file instance again
        cssfile = FakeCSSFile(fname=source_path, conf=conf, data=css)

        # Output rewritten CSS with spritemapped URLs
        replacer = SpriteReplacer(sm_plcs)
        for data in iter_print_css(replacer(cssfile)):
            out.write(data)
