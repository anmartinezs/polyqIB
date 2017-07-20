%% Runs filter_motl_within_dist_to_points.m with a motive list file, points mask file and a distance cutoff and saves the filtered motive list to a file.
%% Then runs visualise_particles_on_tomo.m with the filtered motive list.

clear all

tomograms = {'t92'}; % TODO: change 't85'
method = 'etomo_cleaned_notcorr_Felix';
disp(['method ' method]);
handedness = 'right_handed';
motl_file = 'motl_membrane_bound_manual.em'; % TODO: change t85: 'motl_with_mask_manual_within_18nm_to_membrane_final.em' 
disp(['motive list: ' handedness '/' motl_file]);
points_mask_file = 'sec61_centers_filtered_bin6.mrc';
dist = 6.78; %7 %maximal distance between ribosome center and (original) Sec61 center in bin 6
filtered_motl_file = 'motl_filtered.em';
binned_twice = 1; % TODO: change (1 if motls are bin3 and points masks bin6)

% tomogram sizes in bin3:
tomo_x = 1180;
tomo_y = tomo_x;
tomo_z = [521]; % TODO: change (same length as tomograms!) 531
ribosome_mapping_file = 'mapped_ribosomes_filtered.mrc';

for i=1:length(tomograms)
    disp(['Tomogram ' tomograms{i}]);
    disp('Filtering motive list...');
    motl = tom_emread([tomograms{i} '/' method '/' handedness '/' motl_file]); motl = motl.Value;
    points_mask = tom_mrcread([tomograms{i} '/' method '/' handedness '/' points_mask_file]); points_mask = points_mask.Value;
    [filtered_motl, distances] = filter_motl_within_dist_to_points(motl, points_mask, dist, binned_twice);
    tom_emwrite([tomograms{i} '/' method '/' handedness '/' filtered_motl_file], filtered_motl);
    figure;
    histogram(distances)
    
    disp('Mapping whole ribosomes with membrane');
    visualise_particles_on_tomo([tomograms{i} '/' method '/' handedness '/' filtered_motl_file], 'reference_with_membrane.em', tomo_x, tomo_y, tomo_z(i), [tomograms{i} '/' method '/' handedness '/' ribosome_mapping_file]);
end

disp('Finished!');