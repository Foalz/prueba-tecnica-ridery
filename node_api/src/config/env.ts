import { z } from 'zod';
import dotenv from 'dotenv';

dotenv.config();

const envSchema = z.object({
  PORT: z.string().default('3000').transform(Number),
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  ODOO_BASE_URL: z.string().url(),
  ODOO_API_KEY: z.string().min(1),
  ODOO_ORIGIN: z.string().url().default('http://localhost:3000'),
  ODOO_TRIPS_PATH: z.string().startsWith('/').default('/ridery/api/v1/trips'),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  console.error('❌ Variables de entorno inválidas:\n');
  Object.entries(parsed.error.flatten().fieldErrors).forEach(([k, v]) => {
    console.error(`  ${k}: ${v?.join(', ')}`);
  });
  console.error('\nCopia .env.example a .env y completa los valores.\n');
  process.exit(1);
}

export const env = parsed.data;
export const ODOO_ENDPOINT = `${env.ODOO_BASE_URL}${env.ODOO_TRIPS_PATH}`;
