from typing import Dict, List
from app.services.llm_adapter import LLMAdapter
from app.services.file_manager import FileManager


class FrontendAgent:
    """Frontend Agent - Generates HTML/Jinja2 templates."""
    
    SYSTEM_PROMPT = """You are an expert frontend developer specialized in building ERP user interfaces with HTML, Jinja2, TailwindCSS, and HTMX.

Your responsibilities:
1. Generate clean, responsive HTML templates
2. Use TailwindCSS for styling
3. Implement HTMX for dynamic interactions
4. Create forms, tables, and data displays
5. Ensure accessibility and user experience

Template structure:
- templates/base.html - Base layout with navigation
- templates/dashboard.html - Main dashboard
- templates/module_list.html - List views
- templates/module_form.html - Create/Edit forms
- templates/module_detail.html - Detail views

Generate production-ready, accessible, and user-friendly templates."""
    
    def __init__(self, llm_adapter: LLMAdapter, file_manager: FileManager):
        self.llm = llm_adapter
        self.file_manager = file_manager
    
    async def generate_frontend(self, project_id: str, prd: Dict) -> Dict[str, any]:
        """Generate complete frontend from PRD."""
        
        try:
            results = {
                "base": await self._generate_base_template(project_id, prd),
                "dashboard": await self._generate_dashboard(project_id, prd),
                "modules": await self._generate_module_templates(project_id, prd),
                "components": await self._generate_components(project_id, prd),
                "static": await self._generate_static_files(project_id, prd)
            }
            
            return {
                "success": True,
                "project_id": project_id,
                "files_generated": results
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_base_template(self, project_id: str, prd: Dict) -> List[str]:
        """Generate base layout template."""
        modules = prd.get("modules", [])
        nav_items = "\n                ".join([
            f'<a href="/{{{{ url_for(\'{m["name"].lower().replace(" ", "_")}_list\') }}}}" class="block px-4 py-2 hover:bg-gray-100">{m["name"]}</a>'
            for m in modules
        ])
        
        template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{% block title %}}{prd.get('project_name', 'ERP System')}{{% endblock %}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body class="bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <div class="flex">
                    <div class="flex-shrink-0 flex items-center">
                        <h1 class="text-xl font-bold text-gray-800">{prd.get('project_name', 'ERP System')}</h1>
                    </div>
                    <div class="ml-10 flex items-baseline space-x-4">
                        <a href="/" class="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100">Dashboard</a>
                        {nav_items}
                    </div>
                </div>
                <div class="flex items-center">
                    <span class="text-gray-700">{{{{ user.name if user else 'Guest' }}}}</span>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {{% block content %}}
        {{% endblock %}}
    </main>

    <!-- Footer -->
    <footer class="bg-white mt-12">
        <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            <p class="text-center text-gray-500 text-sm">
                © 2024 {prd.get('project_name', 'ERP System')}. All rights reserved.
            </p>
        </div>
    </footer>
</body>
</html>"""
        
        filename = "frontend/templates/base.html"
        self.file_manager.write_file(project_id, filename, template)
        
        return [filename]
    
    async def _generate_dashboard(self, project_id: str, prd: Dict) -> List[str]:
        """Generate dashboard template."""
        modules = prd.get("modules", [])
        
        module_cards = "\n            ".join([
            f"""<div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <h3 class="text-lg font-medium text-gray-900">{m['name']}</h3>
                    <p class="mt-1 text-sm text-gray-500">{m.get('description', '')}</p>
                    <div class="mt-4">
                        <a href="/{{{{ url_for('{m['name'].lower().replace(' ', '_')}_list') }}}}" class="text-indigo-600 hover:text-indigo-900">View →</a>
                    </div>
                </div>
            </div>"""
            for m in modules
        ])
        
        template = f"""{{% extends "base.html" %}}

{{% block title %}}Dashboard - {prd.get('project_name', 'ERP System')}{{% endblock %}}

{{% block content %}}
<div class="px-4 py-6 sm:px-0">
    <h2 class="text-2xl font-bold text-gray-900 mb-6">Dashboard</h2>
    
    <!-- Stats -->
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 mb-8">
        {module_cards}
    </div>
    
    <!-- Recent Activity -->
    <div class="bg-white shadow rounded-lg p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
        <div id="recent-activity" hx-get="/api/recent-activity" hx-trigger="load">
            <p class="text-gray-500">Loading...</p>
        </div>
    </div>
</div>
{{% endblock %}}"""
        
        filename = "frontend/templates/dashboard.html"
        self.file_manager.write_file(project_id, filename, template)
        
        return [filename]
    
    async def _generate_module_templates(self, project_id: str, prd: Dict) -> List[str]:
        """Generate templates for each module."""
        files_created = []
        
        modules = prd.get("modules", [])
        entities = prd.get("entities", [])
        
        for module in modules:
            module_name = module['name'].lower().replace(' ', '_')
            
            # Find related entity
            entity = next((e for e in entities if e['name'].lower() in module_name), 
                         entities[0] if entities else None)
            
            if not entity:
                continue
            
            # List view
            list_template = await self._generate_list_view(project_id, module, entity)
            files_created.append(list_template)
            
            # Form view
            form_template = await self._generate_form_view(project_id, module, entity)
            files_created.append(form_template)
            
            # Detail view
            detail_template = await self._generate_detail_view(project_id, module, entity)
            files_created.append(detail_template)
        
        return files_created
    
    async def _generate_list_view(self, project_id: str, module: Dict, entity: Dict) -> str:
        """Generate list view template."""
        module_name = module['name'].lower().replace(' ', '_')
        
        # Generate table headers
        fields = entity.get('fields', [])
        headers = "\n                        ".join([
            f'<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{f["name"]}</th>'
            for f in fields[:5]  # Limit to first 5 fields
        ])
        
        # Generate table cells
        cells = "\n                        ".join([
            f'<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{{{ item.{f["name"]} }}}}</td>'
            for f in fields[:5]
        ])
        
        template = f"""{{% extends "base.html" %}}

{{% block title %}}{module['name']} - {entity['name']}s{{% endblock %}}

{{% block content %}}
<div class="px-4 py-6 sm:px-0">
    <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-900">{module['name']}</h2>
        <a href="/{module_name}/create" class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">
            Add New
        </a>
    </div>
    
    <!-- Search and Filters -->
    <div class="mb-4">
        <input type="text" placeholder="Search..." 
               class="w-full px-4 py-2 border rounded-md"
               hx-get="/{module_name}/search" 
               hx-trigger="keyup changed delay:500ms"
               hx-target="#items-list">
    </div>
    
    <!-- Table -->
    <div class="bg-white shadow rounded-lg overflow-hidden">
        <div id="items-list">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        {headers}
                        <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {{% for item in items %}}
                    <tr>
                        {cells}
                        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <a href="/{module_name}/{{{{ item.id }}}}" class="text-indigo-600 hover:text-indigo-900 mr-4">View</a>
                            <a href="/{module_name}/{{{{ item.id }}}}/edit" class="text-green-600 hover:text-green-900 mr-4">Edit</a>
                            <button hx-delete="/{module_name}/{{{{ item.id }}}}" 
                                    hx-confirm="Are you sure?"
                                    class="text-red-600 hover:text-red-900">Delete</button>
                        </td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>
    </div>
</div>
{{% endblock %}}"""
        
        filename = f"frontend/templates/{module_name}_list.html"
        self.file_manager.write_file(project_id, filename, template)
        
        return filename
    
    async def _generate_form_view(self, project_id: str, module: Dict, entity: Dict) -> str:
        """Generate form template."""
        module_name = module['name'].lower().replace(' ', '_')
        
        # Generate form fields
        fields = entity.get('fields', [])
        form_fields = []
        
        for field in fields:
            if field['name'] in ['id', 'created_at', 'updated_at']:
                continue
            
            field_type = field.get('type', 'string')
            input_type = 'text'
            
            if 'email' in field['name'].lower():
                input_type = 'email'
            elif 'password' in field['name'].lower():
                input_type = 'password'
            elif field_type == 'integer':
                input_type = 'number'
            elif field_type == 'date':
                input_type = 'date'
            
            form_fields.append(f"""
            <div>
                <label class="block text-sm font-medium text-gray-700">{field['name'].replace('_', ' ').title()}</label>
                <input type="{input_type}" name="{field['name']}" 
                       class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                       {'required' if field.get('required') else ''}>
            </div>""")
        
        form_fields_html = "\n            ".join(form_fields)
        
        template = f"""{{% extends "base.html" %}}

{{% block title %}}{{% if item %}}Edit{{% else %}}Create{{% endif %}} {entity['name']}{{% endblock %}}

{{% block content %}}
<div class="px-4 py-6 sm:px-0">
    <h2 class="text-2xl font-bold text-gray-900 mb-6">
        {{% if item %}}Edit{{% else %}}Create{{% endif %}} {entity['name']}
    </h2>
    
    <div class="bg-white shadow rounded-lg p-6 max-w-2xl">
        <form hx-post="/{module_name}{{% if item %}}/{{{{ item.id }}}}{{% endif %}}" 
              hx-target="#form-result"
              class="space-y-6">
            {form_fields_html}
            
            <div class="flex justify-end space-x-4">
                <a href="/{module_name}" class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
                    Cancel
                </a>
                <button type="submit" class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                    {{% if item %}}Update{{% else %}}Create{{% endif %}}
                </button>
            </div>
        </form>
        
        <div id="form-result" class="mt-4"></div>
    </div>
</div>
{{% endblock %}}"""
        
        filename = f"frontend/templates/{module_name}_form.html"
        self.file_manager.write_file(project_id, filename, template)
        
        return filename
    
    async def _generate_detail_view(self, project_id: str, module: Dict, entity: Dict) -> str:
        """Generate detail view template."""
        module_name = module['name'].lower().replace(' ', '_')
        
        fields = entity.get('fields', [])
        detail_fields = "\n                ".join([
            f"""<div class="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4">
                    <dt class="text-sm font-medium text-gray-500">{f['name'].replace('_', ' ').title()}</dt>
                    <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{{{{ item.{f['name']} }}}}</dd>
                </div>"""
            for f in fields
        ])
        
        template = f"""{{% extends "base.html" %}}

{{% block title %}}{entity['name']} Details{{% endblock %}}

{{% block content %}}
<div class="px-4 py-6 sm:px-0">
    <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-900">{entity['name']} Details</h2>
        <div class="space-x-2">
            <a href="/{module_name}/{{{{ item.id }}}}/edit" class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">
                Edit
            </a>
            <a href="/{module_name}" class="bg-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-400">
                Back
            </a>
        </div>
    </div>
    
    <div class="bg-white shadow rounded-lg overflow-hidden">
        <dl class="divide-y divide-gray-200">
            {detail_fields}
        </dl>
    </div>
</div>
{{% endblock %}}"""
        
        filename = f"frontend/templates/{module_name}_detail.html"
        self.file_manager.write_file(project_id, filename, template)
        
        return filename
    
    async def _generate_components(self, project_id: str, prd: Dict) -> List[str]:
        """Generate reusable components."""
        # Pagination component
        pagination = """{{% macro pagination(page, total_pages, url_base) %}}
<div class="flex justify-between items-center mt-6">
    <div class="text-sm text-gray-700">
        Page {{ page }} of {{ total_pages }}
    </div>
    <div class="space-x-2">
        {{% if page > 1 %}}
            <a href="{{ url_base }}?page={{ page - 1 }}" class="px-3 py-2 bg-white border rounded-md hover:bg-gray-50">Previous</a>
        {{% endif %}}
        {{% if page < total_pages %}}
            <a href="{{ url_base }}?page={{ page + 1 }}" class="px-3 py-2 bg-white border rounded-md hover:bg-gray-50">Next</a>
        {{% endif %}}
    </div>
</div>
{{% endmacro %}}"""
        
        filename = "frontend/templates/components/pagination.html"
        self.file_manager.write_file(project_id, filename, pagination)
        
        return [filename]
    
    async def _generate_static_files(self, project_id: str, prd: Dict) -> List[str]:
        """Generate static CSS and JS files."""
        # Custom CSS
        css = """/* Custom styles */
.htmx-indicator {
    display: none;
}

.htmx-request .htmx-indicator {
    display: inline;
}

.htmx-request.htmx-indicator {
    display: inline;
}"""
        
        css_file = "frontend/static/css/custom.css"
        self.file_manager.write_file(project_id, css_file, css)
        
        # Custom JS
        js = """// Custom JavaScript
document.body.addEventListener('htmx:afterSwap', function(evt) {
    console.log('HTMX content swapped');
});"""
        
        js_file = "frontend/static/js/custom.js"
        self.file_manager.write_file(project_id, js_file, js)
        
        return [css_file, js_file]
