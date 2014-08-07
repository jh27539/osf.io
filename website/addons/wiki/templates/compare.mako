<%inherit file="base.mako"/>
<%def name="content()">

<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<div class="wiki">
    <div class="row">
        <div class="col-md-3">
            <%include file="wiki/templates/nav.mako"/>
            <%include file="wiki/templates/toc.mako"/>
        </div>
        <div class="col-md-9">
            <%include file="wiki/templates/status.mako/"/>
        </div>
        <div class="col-md-6 wiki">
            ${wiki_content}
        </div>
        <div class="col-md-3">
            <%include file="wiki/templates/history.mako" />
        </div>
    </div>
</div>

<script type="text/javascript">
    window.onload = function() {
        var version = window.location.pathname.split('/').pop();
        $('#wikiName').append('</h3></br><h5><span>Version: </span>' + version + '</h5>' );
    }
</script>

</%def>

