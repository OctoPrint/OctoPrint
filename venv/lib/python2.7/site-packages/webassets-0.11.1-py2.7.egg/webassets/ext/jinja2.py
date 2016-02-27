from __future__ import absolute_import

import warnings
import jinja2
from jinja2.ext import Extension
from jinja2 import nodes
from webassets import Bundle
from webassets.loaders import GlobLoader, LoaderError
from webassets.exceptions import ImminentDeprecationWarning


__all__ = ('assets', 'Jinja2Loader',)


class AssetsExtension(Extension):
    """
    As opposed to the Django tag, this tag is slightly more capable due
    to the expressive powers inherited from Jinja. For example:

        {% assets "src1.js", "src2.js", get_src3(),
                  filter=("jsmin", "gzip"), output=get_output() %}
        {% endassets %}
    """

    tags = set(['assets'])

    BundleClass = Bundle   # Helpful for mocking during tests.

    def __init__(self, environment):
        super(AssetsExtension, self).__init__(environment)

        # Add the defaults to the environment
        environment.extend(
            assets_environment=None,
        )

    def parse(self, parser):
        lineno = next(parser.stream).lineno

        files = []
        output = nodes.Const(None)
        filters = nodes.Const(None)
        dbg = nodes.Const(None)
        depends = nodes.Const(None)

        # Parse the arguments
        first = True
        while parser.stream.current.type != 'block_end':
            if not first:
                parser.stream.expect('comma')
            first = False

            # Lookahead to see if this is an assignment (an option)
            if parser.stream.current.test('name') and parser.stream.look().test('assign'):
                name = next(parser.stream).value
                parser.stream.skip()
                value = parser.parse_expression()
                if name == 'filters':
                    filters = value
                elif name == 'filter':
                    filters = value
                    warnings.warn('The "filter" option of the {%% assets %%} '
                                  'template tag has been renamed to '
                                  '"filters" for consistency reasons '
                                  '(line %s).' % lineno,
                                    ImminentDeprecationWarning)
                elif name == 'output':
                    output = value
                elif name == 'debug':
                    dbg = value
                elif name == 'depends':
                    depends = value
                else:
                    parser.fail('Invalid keyword argument: %s' % name)
            # Otherwise assume a source file is given, which may be any
            # expression, except note that strings are handled separately above.
            else:
                expression = parser.parse_expression()
                if isinstance(expression, (nodes.List, nodes.Tuple)):
                    files.extend(expression.iter_child_nodes())
                else:
                    files.append(expression)

        # Parse the contents of this tag
        body = parser.parse_statements(['name:endassets'], drop_needle=True)

        # We want to make some values available to the body of our tag.
        # Specifically, the file url(s) (ASSET_URL), and any extra dict set in
        # the bundle (EXTRA).
        #
        # A short interlope: I would have preferred to make the values of the
        # extra dict available directly. Unfortunately, the way Jinja2 does
        # things makes this problematic. I'll explain.
        #
        # Jinja2 generates Python code from it's AST which it then executes.
        # So the way extensions implement making custom variables available to
        # a block of code is by generating a ``CallBlock``, which essentially
        # wraps our child nodes in a Python function. The arguments of this
        # function are the values that are available to our tag contents.
        #
        # But we need to generate this ``CallBlock`` now, during parsing, and
        # right now we don't know the actual ``Bundle.extra`` values yet. We
        # only resolve the bundle during rendering!
        #
        # This would easily be solved if Jinja2 where to allow extensions to
        # scope it's context, which is a dict of values that templates can
        # access, just like in Django (you might see on occasion
        # ``context.resolve('foo')`` calls in Jinja2's generated code).
        # However, it seems the context is essentially only for the initial
        # set of data passed to render(). There are some statements by Armin
        # that this might change at some point, but I've run into this problem
        # before, and I'm not holding my breath.
        #
        # I **really** did try to get around this, including crazy things like
        # inserting custom Python code by patching the tag child nodes::
        #
        #        rv = object.__new__(nodes.InternalName)
        #        # l_EXTRA is the argument we defined for the CallBlock/Macro
        #        # Letting Jinja define l_kwargs is also possible
        #        nodes.Node.__init__(rv, '; context.vars.update(l_EXTRA)',
        #                            lineno=lineno)
        #        # Scope required to ensure our code on top
        #        body = [rv, nodes.Scope(body)]
        #
        # This custom code would run at the top of the function in which the
        # CallBlock node would wrap the code generated from our tag's child
        # nodes. Note that it actually does works, but doesn't clear the values
        # at the end of the scope).
        #
        # If it is possible to do this, it certainly isn't reasonable/
        #
        # There is of course another option altogether: Simple resolve the tag
        # definition to a bundle right here and now, thus get access to the
        # extra dict, make all values arguments to the CallBlock (Limited to
        # 255 arguments to a Python function!). And while that would work fine
        # in 99% of cases, it wouldn't be correct. The compiled template could
        # be cached and used with different bundles/environments, and this
        # would require the bundle to resolve at parse time, and hardcode it's
        # extra values.
        #
        # Interlope end.
        #
        # Summary: We have to be satisfied with a single EXTRA variable.
        args = [nodes.Name('ASSET_URL', 'store'),
                nodes.Name('EXTRA', 'store')]

        # Return a ``CallBlock``, which means Jinja2 will call a Python method
        # of ours when the tag needs to be rendered. That method can then
        # render the template body.
        call = self.call_method(
            # Note: Changing the args here requires updating ``Jinja2Loader``
            '_render_assets', args=[filters, output, dbg, depends, nodes.List(files)])
        call_block = nodes.CallBlock(call, args, [], body)
        call_block.set_lineno(lineno)
        return call_block

    @classmethod
    def resolve_contents(cls, contents, env):
        """Resolve bundle names."""
        result = []
        for f in contents:
            try:
                result.append(env[f])
            except KeyError:
                result.append(f)
        return result

    def _render_assets(self, filter, output, dbg, depends, files, caller=None):
        env = self.environment.assets_environment
        if env is None:
            raise RuntimeError('No assets environment configured in '+
                               'Jinja2 environment')

        # Construct a bundle with the given options
        bundle_kwargs = {
            'output': output,
            'filters': filter,
            'debug': dbg,
            'depends': depends,
        }
        bundle = self.BundleClass(
            *self.resolve_contents(files, env), **bundle_kwargs)

        # Retrieve urls (this may or may not cause a build)
        with bundle.bind(env):
            urls = bundle.urls()

        # For each url, execute the content of this template tag (represented
        # by the macro ```caller`` given to use by Jinja2).
        result = u""
        for url in urls:
            result += caller(url, bundle.extra)
        return result


assets = AssetsExtension  # nicer import name


class Jinja2Loader(GlobLoader):
    """Parse all the Jinja2 templates in the given directory, try to
    find bundles in active use.

    Try all the given environments to parse the template, until we
    succeed.
    """

    def __init__(self, assets_env, directories, jinja2_envs, charset='utf8', jinja_ext='*.html'):
        self.asset_env = assets_env
        self.directories = directories
        self.jinja2_envs = jinja2_envs
        self.charset = charset
        self.jinja_ext = jinja_ext

    def load_bundles(self):
        bundles = []
        for template_dir in self.directories:
            for filename in self.glob_files((template_dir, self.jinja_ext)):
                bundles.extend(self.with_file(filename, self._parse) or [])
        return bundles

    def _parse(self, filename, contents):
        for i, env in enumerate(self.jinja2_envs):
            try:
                t = env.parse(contents.decode(self.charset))
            except jinja2.exceptions.TemplateSyntaxError as e:
                #print ('jinja parser (env %d) failed: %s'% (i, e))
                pass
            else:
                result = []
                def _recurse_node(node_to_search):
                    for node in node_to_search.iter_child_nodes():
                        if isinstance(node, jinja2.nodes.Call):
                            if isinstance(node.node, jinja2.nodes.ExtensionAttribute)\
                               and node.node.identifier == AssetsExtension.identifier:
                                filter, output, dbg, depends, files = node.args
                                bundle = Bundle(
                                    *AssetsExtension.resolve_contents(files.as_const(), self.asset_env),
                                    **{
                                        'output': output.as_const(),
                                        'depends': depends.as_const(),
                                        'filters': filter.as_const()})
                                result.append(bundle)
                        else:
                            _recurse_node(node)
                for node in t.iter_child_nodes():
                    _recurse_node(node)
                return result
        else:
            raise LoaderError('Jinja parser failed on %s, tried %d environments' % (
                filename, len(self.jinja2_envs)))
        return False
