import fs from 'fs/promises';
import path from 'path';
import { RawTrip } from '../types/trip.types';

const DATA_PATH =
  process.env.TRIPS_DATA_PATH ??
  path.resolve(process.cwd(), 'src', 'data', 'trips.json');

export async function readTrips(): Promise<RawTrip[]> {
  const raw = await fs.readFile(DATA_PATH, 'utf-8');
  return JSON.parse(raw) as RawTrip[];
}

export async function writeTrips(trips: RawTrip[]): Promise<void> {
  await fs.writeFile(DATA_PATH, JSON.stringify(trips, null, 2), 'utf-8');
}
