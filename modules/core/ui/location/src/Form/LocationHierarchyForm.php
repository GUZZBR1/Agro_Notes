<?php

declare(strict_types=1);

namespace Drupal\farm_ui_location\Form;

use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Url;
use Drupal\asset\Entity\AssetInterface;

/**
 * Form for changing the hierarchy of all location assets.
 *
 * @ingroup farm
 */
class LocationHierarchyForm extends BaseLocationHierarchyForm {

  /**
   * {@inheritdoc}
   */
  public function getFormId() {
    return 'farm_ui_location_location_form';
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state, ?AssetInterface $asset = NULL) {

    // Show a map of all locations.
    $form['map'] = [
      '#type' => 'farm_map',
      '#map_type' => 'locations',
    ];

    // Build location form.
    return parent::buildLocationForm(
      $form,
      (string) $this->t('All locations'),
      Url::fromRoute('farm.locations'),
      $this->buildTree(),
    );
  }

}
