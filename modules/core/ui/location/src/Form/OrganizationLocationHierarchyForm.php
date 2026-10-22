<?php

declare(strict_types=1);

namespace Drupal\farm_ui_location\Form;

use Drupal\Core\Entity\Query\QueryInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\asset\Entity\AssetInterface;
use Drupal\organization\Entity\OrganizationInterface;

/**
 * Form for changing the hierarchy of location assets within an organization.
 *
 * @ingroup farm
 */
class OrganizationLocationHierarchyForm extends BaseLocationHierarchyForm {

  /**
   * {@inheritdoc}
   */
  public function getFormId() {
    return 'farm_ui_location_organization_location_form';
  }

  /**
   * Generate the page title.
   *
   * @param \Drupal\organization\Entity\OrganizationInterface $organization
   *   The organization this page is being built for.
   *
   * @return \Drupal\Core\StringTranslation\TranslatableMarkup
   *   Returns the translated page title.
   */
  public function getTitle(OrganizationInterface $organization) {
    return $this->t('Locations in %organization', ['%organization' => $organization->label()]);
  }

  /**
   * {@inheritdoc}
   */
  public function buildForm(array $form, FormStateInterface $form_state, ?OrganizationInterface $organization = NULL) {

    // Bail if there is no organization.
    if (!$organization) {
      return $form;
    }

    // Show a map of organization locations.
    $form['map'] = [
      '#type' => 'farm_map',
      '#map_type' => 'locations',
      '#location_filters' => [
        'farm_target_id' => $organization->label(),
      ],
    ];

    // Build location form.
    return parent::buildLocationForm(
      $form,
      $organization->label(),
      $organization->toUrl('canonical'),
      $this->buildTree(),
    );
  }

  /**
   * {@inheritdoc}
   */
  protected function getLocationQuery(?AssetInterface $parent = NULL): QueryInterface {

    // Add farm organization condition to query.
    $query = parent::getLocationQuery($parent);
    if ($organization = $this->getRouteMatch()->getParameter('organization')) {
      $query->condition('farm', $organization->id());
    }
    return $query;
  }

}
