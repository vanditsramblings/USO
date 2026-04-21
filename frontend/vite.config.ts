import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/api': 'http://localhost:8000',
			'/ws': { target: 'ws://localhost:8000', ws: true },
			'/health': 'http://localhost:8000'
		}
	}
});
